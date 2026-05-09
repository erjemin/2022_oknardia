/**
 * Логика записи визитов пользователя в cookies.
 * Отслеживает последние посещения страниц с ценовой выдачей.
 *
 * Используемые данные из HTML:
 * - data-current-url: текущий URL страницы
 * - data-address: адрес здания
 * - data-apart: тип квартиры
 *
 * Сохраняет в куку 'LastVisit' максимум 3 последних визита в формате JSON.
 */

function trackUserVisit(currentUrl, address, apart) {
  // Функция для получения значения куки по имени
  function getCookieValue(name) {
    try {
      if (document.cookie) {
        const cookies = document.cookie.split('; ');
        for (let cookie of cookies) {
          const [cookieName, cookieValue] = cookie.split('=');
          if (cookieName === name) {
            return decodeURIComponent(cookieValue);
          }
        }
      }
    } catch (e) {
      console.warn('Ошибка при чтении куки:', e);
    }
    return null;
  }

  // Функция для установки куки с заданным сроком жизни
  function setCookie(name, value, maxAge) {
    try {
      const cookieValue = encodeURIComponent(value);
      let cookieString = `${name}=${cookieValue}; path=/`;
      if (maxAge) {
        cookieString += `; max-age=${maxAge}`;
      }
      document.cookie = cookieString;
    } catch (e) {
      console.warn('Ошибка при установке куки:', e);
    }
  }

  // Получаем последние визиты из куки (если есть)
  let lastVisits = [];
  const cookieValue = getCookieValue('LastVisit');
  if (cookieValue) {
    try {
      lastVisits = JSON.parse(cookieValue);
    } catch (e) {
      console.warn('Ошибка при разборе JSON из куки LastVisit:', e);
      lastVisits = [];
    }
  }

  // Создаём новый item посещения с текущей информацией
  const newItem = {
    LastURL: currentUrl,
    LastAddress: address,
    LastApart: apart,
    Time: performance.now() // используем performance.now() как аналог time.perf_counter() в Python
  };

  // Добавляем новый item в начало списка
  lastVisits.unshift(newItem);

  // Оставляем максимум 3 последних записи
  lastVisits = lastVisits.slice(0, 4);

  // Упаковываем в JSON (JSON.stringify без пробелов для компактности)
  const jsonData = JSON.stringify(lastVisits);

  // Устанавливаем куки на 91 день (7862400 секунд)
  setCookie('LastVisit', jsonData, 7862400);
}

/**
 * Инициализация отслеживания при загрузке документа.
 * Ищет элемент с атрибутами data-current-url, data-address, data-apart
 * и вызывает trackUserVisit с полученными значениями.
 */
document.addEventListener('DOMContentLoaded', function() {
  // Ищем элемент со встроенными данными (например, скрытый div в шаблоне)
  const trackingElement = document.querySelector('[data-current-url]');

  if (trackingElement) {
    const currentUrl = trackingElement.getAttribute('data-current-url');
    const address = trackingElement.getAttribute('data-address');
    const apart = trackingElement.getAttribute('data-apart');

    if (currentUrl && address && apart) {
      trackUserVisit(currentUrl, address, apart);
    }
  }
});

