/*!
 * ОКНАРДИЯ LOGIN-LOGOUT.JS
 * Copyright 2015 Sergei Erjemin
 * СОЗДАНО ДЛЯ ПРОЕКТА ОКНАРДИЯ
 */
let REG = 0;
function in_ntr(){ // колапсаторы для раздела ВОЙТИ
  REG = 0;
  $('#ili').collapse('hide');
  $('#mail').collapse('hide');
  $('#pwd1').collapse('show');
  $('#pwd2').collapse('hide');
  $('#capt').collapse('hide');
  $('#b_vost').collapse('hide');
  $('#b_reg').collapse('hide');
  $('#b_vhod').collapse('show');
  $('#pwd_comment').collapse('hide');
  $('#pwd_comment_text').text('Шесть (или более) букв (прописных и строчных) и цифр');
}
in_ntr(); // установить колапсаторы в исходное состояние --> раздел ВОЙТИ
function in_reg(){ // колапсаторы для раздела РЕГИСТРАИЦЯ
  REG = 1;
  $('#ili').collapse('hide');
  $('#mail').collapse('show');
  $('#pwd1').collapse('show');
  $('#pwd2').collapse('show');
  $('#capt').collapse('hide');
  $('#b_vhod').collapse('hide');
  $('#b_vost').collapse('hide');
  $('#b_reg').collapse('show');
  $('#pwd_comment').collapse('hide');
}
function in_vost(){ // колапсаторы для раздела ВОССТАНОВИТЬ ПАРОЛЬ
  REG = 1;
  $('#ili').collapse('show');
  $('#mail').collapse('show');
  $('#pwd1').collapse('hide');
  $('#pwd2').collapse('hide');
  $('#capt').collapse('show');
  $('#b_vhod').collapse('hide');
  $('#b_reg').collapse('hide');
  $('#captcha').load('/captcha'); // подгрузить GOOGLE CAPTCHA
  $('#b_vost').collapse('show');
  $('#pwd_comment').collapse('hide');
}

$(document).ready(function(){
  //in_ntr(); // установить колапсаторы в исходное состояние --> раздел ВОЙТИ

  // ЕСЛИ ЗАПРОСИЛИ LOGIN, РЕГИСТРАЦИЮ или ВОССТАНОВЛЕНИЕ ПАРОЛЯ
  $('#login-reg-restore-form').submit(
    function enter(){
      $.ajax({
        url:     "/form-loginout", //Адрес подгружаемой страницы
        type:     "POST", //Тип запроса
        dataType: "html", //Тип данных
        data: $("#login-reg-restore-form").serialize(),
        success: function(html){ $("#login-logout").html(html)}
        });
      return false;
      }
    );

  // ЕСЛИ ЗАПРОСИЛИ LOGOUT
  $('#logout-form').submit(
    function enter(){
      $.ajax({
        url:     "/form-loginout", //Адрес подгружаемой страницы
        type:     "POST", //Тип запроса
        dataType: "html", //Тип данных
        data: $("#logout-form").serialize(),
        success: function(html){ $("#login-logout").html(html)}
        });
      return false;
      }
    );

  // ВАЛИДАЦИЯ E-MAIL
  $("#email").keyup(function(){
    let pattern = new RegExp(/^(("[\w-\s]+")|([\w-]+(?:\.[\w-]+)*)|("[\w-\s]+")([\w-]+(?:\.[\w-]+)*))(@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$)|(@\[?((25[0-5]\.|2[0-4][0-9]\.|1[0-9]{2}\.|[0-9]{1,2}\.))((25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2})\.){2}(25[0-5]|2[0-4][0-9]|1[0-9]{2}|[0-9]{1,2})\]?$)/i);
    if( $(this).val() != '')
      if( pattern.test( $(this).val() ) )
        $("#valid-email").css({ "color": "green" });
      else
        $("#valid-email").css({ "color": "red"  });
    else
      $("#valid-email").css({ "color": "white" });
    });

  // ПРОВЕРКА ДЛИННЫ ЛОГИНА
  $("#username").keyup(function(){
    if( $(this).val() != '')
      if( $(this).val().length >= 4  )
        $("#valid-username").css({ "color": "green" });
      else
        $("#valid-username").css({ "color": "red"  });
    else
      $("#valid-username").css({ "color": "white" });
    });


  // ПРОВЕРКА КАЧЕСТВА ПАРОЛЯ
  $("#password").keyup(function(){
    let ucase = new RegExp("[A-Z]+"), lcase = new RegExp("[a-z]+"), num = new RegExp("[0-9]+");
    if( $(this).val() != '' && REG == 1 )
      if( $(this).val().length >= 6  )
        if( ucase.test($(this).val()) && lcase.test($(this).val()) && num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "green" });
          $('#pwd_comment_text').text("Отличный пароль!");
          $("#pwd_comment").css({ "color": "green" });
          }
        else if ( ucase.test($(this).val()) && lcase.test($(this).val()) ) {
          $("#valid-password").css({ "color": "grey" });
          $('#pwd_comment_text').text("Хороший пароль! Не хватает цифр.");
          $("#pwd_comment").css({ "color": "green" });
          }
        else if ( lcase.test($(this).val()) && num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "grey" });
          $('#pwd_comment_text').text("Хороший пароль! Не хватает прописных букв.");
          $("#pwd_comment").css({ "color": "green" });
          }
        else if ( ucase.test($(this).val()) && num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "grey" });
          $('#pwd_comment_text').text("Хороший пароль! Не хватает строчных букв.");
          $("#pwd_comment").css({ "color": "green" });
          }
        else if ( ucase.test($(this).val()) ) {
          $("#valid-password").css({ "color": "orange" });
          $('#pwd_comment_text').text("Слабый пароль! Не хватает цифр и строчных букв.");
          $("#pwd_comment").css({ "color": "orange" });
          }
        else if ( lcase.test($(this).val()) ) {
          $("#valid-password").css({ "color": "orange" });
          $('#pwd_comment_text').text("Слабый пароль! Не хватает цифр и прописных букв.");
          $("#pwd_comment").css({ "color": "orange" });
          }
        else if ( num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "orange" });
          $('#pwd_comment_text').text("Слабый пароль! Не хватает букв.");
          $("#pwd_comment").css({ "color": "orange" });
          }
        else {
          $("#valid-password").css({ "color": "grey" });
          $('#pwd_comment_text').text("Странный пароль! Вы точно сможете его замнить?");
          $("#pwd_comment").css({ "color": "grey" });
          }
      else
        if( ucase.test($(this).val()) && lcase.test($(this).val()) && num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "grey" });
          $('#pwd_comment_text').text("Хороший пароль!.. но короткий.");
          $("#pwd_comment").css({ "color": "grey" });
          }
        else if ( ucase.test($(this).val()) && lcase.test($(this).val()) ) {
          $("#valid-password").css({ "color": "orange" });
          $('#pwd_comment_text').text("Короткий пароль!.. и нет цифр.");
          $("#pwd_comment").css({ "color": "orange" });
          }
        else if ( lcase.test($(this).val()) && num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "orange" });
          $('#pwd_comment_text').text("Короткий пароль!.. и нет прописных букв.");
          $("#pwd_comment").css({ "color": "orange" });
          }
        else if ( ucase.test($(this).val()) && num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "orange" });
          $('#pwd_comment_text').text("Короткий пароль!.. и нет строчных букв.");
          $("#pwd_comment").css({ "color": "orange" });
          }
        else if ( ucase.test($(this).val()) ) {
          $("#valid-password").css({ "color": "red" });
          $('#pwd_comment_text').text("Короткий пароль!.. и нет строчных букв и цифр.");
          $("#pwd_comment").css({ "color": "red" });
          }
        else if ( lcase.test($(this).val()) ) {
          $("#valid-password").css({ "color": "red" });
          $('#pwd_comment_text').text("Короткий пароль!.. и нет прописных букв и цифр.");
          $("#pwd_comment").css({ "color": "red" });
          }
        else if ( num.test($(this).val()) ) {
          $("#valid-password").css({ "color": "red" });
          $('#pwd_comment_text').text("Короткий пароль!.. и нет букв.");
          $("#pwd_comment").css({ "color": "red" });
          }
        else {
          $("#valid-password").css({ "color": "red" });
          $('#pwd_comment_text').text("Странныйе символы! Переключитесь на латиницу!");
          $("#pwd_comment").css({ "color": "red" });
          }
    else {
      $("#valid-password").css({ "color": "white" });
      $('#pwd_comment_text').text('Шесть (или более) букв (прописных и строчных) и цифр');
      $("#pwd_comment").css({ "color": "grey" });
      }
    });


  // ПОДСВЕТИТЬ ПОДСКАЗКУ ПРИ НАБОРЕ ПАРОЛЯ
  $("#password").focus(function(){
    if ( REG == 1 ) $('#pwd_comment').collapse('show');
    });
  $("#password").blur(function(){
    if ( REG == 1 ) $('#pwd_comment').collapse('hide');
    });


  // КНОПОЧКИ "ПОДГЛЯДИЕТЬ ПАРОЛЬ" на основном поле PASSWORD
  $("#look_pwd1").mousedown(function() {
    $("#password").attr('type', 'text');
    });
  $("#look_pwd1").mouseup(function() {
    $("#password").attr('type', 'password');
    });
  $("#look_pwd1").mouseout(function() {
    $("#password").attr('type', 'password');
    });


  // КНОПОЧКИ "ПОДГЛЯДИЕТЬ ПАРОЛЬ" на поле "ПОВТОРИТЬ PASSWORD"
  $("#look_pwd2").mousedown(function() {
    $("#password").attr('type', 'text');
    $("#password_repeat").attr('type', 'text');
    });
  $("#look_pwd2").mouseup(function() {
    $("#password").attr('type', 'password');
    $("#password_repeat").attr('type', 'password');
    });
  $("#look_pwd2").mouseout(function() {
    $("#password").attr('type', 'password');
    $("#password_repeat").attr('type', 'password');
    });

  // ПРОВЕРКА КОНТРОЛЬНОГО ПАРОЛЯ
  $("#password_repeat").keyup(function(){
    if( $(this).val() != '')
      if( $(this).val() == $('#password').val() )
        $("#valid-password-repeat").css({ "color": "green" });
      else
        $("#valid-password-repeat").css({ "color": "red"  });
    else
      $("#valid-password-repeat").css({ "color": "white" });
    });

  });

