/**
 * Модуль авторизации: управление dropdown меню логина/логаута
 * Открывает/закрывает меню авторизации с загрузкой контента по AJAX
 *
 *
 * Открывает или закрывает dropdown меню логина/логаута
 * При первом открытии загружает содержимое меню по AJAX
 *
 * @param {Event} event - объект события клика (опционально)
 * @returns {boolean} false - для предотвращения перезагрузки страницы
 */
function openLoginLogout(event) {
  // Предотвращаем переход по ссылке
  if (event) event.preventDefault();

  // Получаем контейнер меню авторизации
  var $box = $('#login-logout');

  /**
   * Переключает видимость dropdown'а
   * Сначала ищет Bootstrap toggle, если нет — вызывает click
   */
  function openDropdown() {
    var $toggle = $box.find('.dropdown-toggle').first();
    if (!$toggle.length) return;
    if (typeof $toggle.dropdown === 'function')
      $toggle.dropdown('toggle');
    else
      $toggle.trigger('click');
  }

  // Если контент ещё не загружен, загружаем его по AJAX
  if (!$box.data('loginLoaded')) {
    $box.load('/login-logout', function () {
      $box.data('loginLoaded', true);
      openDropdown();
    });
  } else {
    // Если уже загружен, просто переключаем видимость
    openDropdown();
  }

  return false;
}

