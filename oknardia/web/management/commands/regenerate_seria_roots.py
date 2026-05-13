# -*- coding: utf-8 -*-
"""
Django management command: regenerate_seria_roots

Пересчет корневых серий (root series) для всех серий домов.

Идея:
Серии домов могут иметь сложную иерархию (дерево потомственности) из-за того,
что на разных сайтах одна и та же серия обозначалась по-разному.
Например серия II-57 записывалась как 2-57, И-57, П-57 и т.п.

Эта команда:
1. Находит "корневые" серии - те, что используются в Apartment_Type (у них есть квартиры)
2. Для всех остальных серий ищет их корневую серию, двигаясь вверх по дереву иерархии
3. Устанавливает найденную корневую серию в поле kRoot_id каждой серии

Результат:
- Все серии-алиасы (синонимы) указывают на одну корневую серию
- Это позволяет консолидировать данные по сериям дома
"""

from django.core.management.base import BaseCommand
from oknardia.models import Seria_Info, Apartment_Type


class Command(BaseCommand):
    help = 'Пересчитывает корневые серии для всей иерархии серий домов'

    def add_arguments(self, parser):
        # Django уже добавляет --verbosity автоматически
        # 0 = минимум (только ошибки)
        # 1 = нормально (точки)
        # 2 = подробно (информация)
        # 3 = очень подробно (таблица)
        pass

    def handle(self, *args, **options):
        verbose = int(options.get('verbosity', 1))

        self.stdout.write(self.style.SUCCESS('=== ПЕРЕСЧЕТ КОРНЕВЫХ СЕРИЙ ===\n'))

        time_start = self.get_time()

        # ========== ЭТАП 1: Находим корневые серии ==========
        if verbose >= 1:
            self.stdout.write('Этап 1: Ищем корневые серии в таблице квартир...\n')

        # Получаем все УНИКАЛЬНЫЕ серии, которые используются в квартирах
        root_series_ids = list(
            Apartment_Type.objects.values_list('kSeria_id', flat=True).distinct()
        )

        # Получаем объекты корневых серий (для вывода их названий)
        root_series = Seria_Info.objects.filter(id__in=root_series_ids)

        if verbose >= 1:
            self.stdout.write(f'✓ Найдено корневых серий: {len(root_series_ids)}\n')

        # Устанавливаем для корневых серий kRoot_id = own_id
        for seria in root_series:
            seria.kRoot_id = seria.id  # Серия сама себе корень
            seria.save()

            if verbose >= 3:
                # Очень подробный вывод - таблица
                self.stdout.write(
                    f'  ✓ {seria.id:04d} | {seria.sName:<30} | корневая'
                )
            elif verbose >= 2:
                # Подробный - с названием
                self.stdout.write(f'  ✓ {seria.id:04d} {seria.sName}')
            elif verbose >= 1:
                # Нормально - точки
                self.stdout.write('.', ending='')

        if verbose < 2:
            self.stdout.write('\n')
        self.stdout.write('')

        # ========== ЭТАП 2: Обрабатываем все серии ==========
        if verbose >= 1:
            self.stdout.write('\nЭтап 2: Главная магия - обрабатываем все серии в иерархии...\n')

        if verbose >= 3:
            # Заголовок таблицы для очень подробного режима
            self.stdout.write('-' * 110)
            self.stdout.write(
                f'{"ID":>5} | {"Название":<35} | {"Родитель":>10} | '
                f'{"Путь":<40} | {"Результат":<20}'
            )
            self.stdout.write('-' * 110)

        all_series = Seria_Info.objects.all()
        count_with_root = 0
        count_without_root = 0
        count_errors = 0
        count_root = 0

        for seria in all_series:
            try:
                # Если это уже корневая серия, пропускаем
                if seria.id in root_series_ids:
                    count_root += 1
                    if verbose >= 3:
                        self.stdout.write(
                            f'{seria.id:>5} | {seria.sName:<35} | '
                            f'{str(seria.kParent_id or "-"):>10} | '
                            f'(корневая) | ✓'
                        )
                    elif verbose >= 2:
                        self.stdout.write(f'  {seria.id:04d}: корневая')
                    elif verbose >= 1:
                        self.stdout.write('.', ending='')
                    continue

                # Движемся вверх по дереву потомок → предок
                current_id = seria.kParent_id
                path_trace = []

                # Рекурсивно ищем корневую серию
                while current_id is not None:
                    path_trace.append(current_id)
                    try:
                        parent_seria = Seria_Info.objects.get(id=current_id)

                        # Проверяем: либо у родителя нет родителя, либо родитель - корневая
                        if parent_seria.kParent_id is None or current_id in root_series_ids:
                            break

                        current_id = parent_seria.kParent_id
                    except Seria_Info.DoesNotExist:
                        current_id = None
                        break

                # Проверяем, что нашли корневую серию
                if current_id and current_id in root_series_ids:
                    seria.kRoot_id = current_id
                    seria.save()

                    if verbose >= 3:
                        path_str = ' → '.join(str(i) for i in path_trace)
                        self.stdout.write(
                            f'{seria.id:>5} | {seria.sName:<35} | '
                            f'{str(seria.kParent_id or "-"):>10} | '
                            f'{path_str:<40} | ✓ Корень #{current_id}'
                        )
                    elif verbose >= 2:
                        self.stdout.write(f'  {seria.id:04d}: корень → {current_id}')
                    elif verbose >= 1:
                        self.stdout.write('+', ending='')

                    count_with_root += 1
                else:
                    seria.kRoot_id = None
                    seria.save()

                    if verbose >= 3:
                        path_str = ' → '.join(str(i) for i in path_trace) if path_trace else '(нет)'
                        self.stdout.write(
                            f'{seria.id:>5} | {seria.sName:<35} | '
                            f'{str(seria.kParent_id or "-"):>10} | '
                            f'{path_str:<40} | ✗ Нет корня'
                        )
                    elif verbose >= 2:
                        self.stdout.write(f'  {seria.id:04d}: Нет корня')
                    elif verbose >= 1:
                        self.stdout.write('-', ending='')

                    count_without_root += 1

            except Exception as e:
                if verbose >= 3:
                    self.stdout.write(
                        self.style.ERROR(f'{seria.id:>5} | ОШИБКА: {str(e):<80}')
                    )
                elif verbose >= 1:
                    self.stdout.write('E', ending='')
                count_errors += 1

        if verbose >= 3:
            self.stdout.write('-' * 110)
        elif verbose < 2:
            self.stdout.write('\n')

        # ========== РЕЗУЛЬТАТЫ ==========
        self.stdout.write(self.style.SUCCESS('\n\n=== РЕЗУЛЬТАТЫ ==='))
        self.stdout.write(f'✓ Корневых серий (обработаны на этапе 1): {count_root}')
        self.stdout.write(f'✓ Серий с найденным корнем: {count_with_root}')
        self.stdout.write(f'⚠ Серий без корня: {count_without_root}')
        if count_errors > 0:
            self.stdout.write(self.style.ERROR(f'✗ Ошибок: {count_errors}'))

        time_elapsed = self.get_time() - time_start
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Пересчет завершен! Время: {time_elapsed:.2f}с')
        )

    @staticmethod
    def get_time():
        import time
        return time.perf_counter()

