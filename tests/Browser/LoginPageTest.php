<?php

/*
 * The login page asks for the username first, and asks for the password only
 * when that account exists.
 */

function loginPageAsk(string $username)
{
    $page = visit('/auth');
    $page->fill('#usernameField', $username);
    $page->click('#submitBtn');

    return $page;
}

it('asks an existing account for its password, and signs it in', function () {
    makeUser('alice', 'Passw0rd!');

    $page = loginPageAsk('alice');
    $page->assertSee('Olá, alice!')->assertPresent('#passwordField')->assertMissing('#emailField');

    $page->fill('#passwordField', 'Passw0rd!');
    $page->click('#submitBtn');

    $page->assertPathIs('/dashboard/home')->assertSee('Olá, alice')->assertNoJavaScriptErrors();
});

it('says so when the password is wrong', function () {
    makeUser('alice', 'Passw0rd!');

    $page = loginPageAsk('alice');
    $page->fill('#passwordField', 'errada');
    $page->click('#submitBtn');

    $page->assertSee('Invalid login.')->assertPathIs('/auth');
});

// Accounts are made from the console; the page used to offer anyone one.
it('tells an unknown name there is no such account, and offers nothing else', function () {
    $page = loginPageAsk('bea');

    $page->assertSee('Não há nenhuma conta com esse nome.')
        ->assertMissing('#passwordField')
        ->assertMissing('#emailField')
        ->assertPathIs('/auth')
        ->assertNoJavaScriptErrors();
});

// The name is written into the greeting, which is HTML.
it('greets an account by name without running it as markup', function () {
    makeUser('<b>alice</b>', 'Passw0rd!', 'alice@example.com');

    $page = loginPageAsk('<b>alice</b>');

    $page->assertSee('Olá, <b>alice</b>!')->assertCount('#form-header b', 0);
});
