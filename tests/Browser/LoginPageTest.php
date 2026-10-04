<?php

/*
 * The login page asks for the username first and draws the next step from the
 * answer: a password for an account that exists, a registration for one that
 * does not.
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

it('offers an unknown name a registration, and signs the new account in', function () {
    $page = loginPageAsk('bea');
    $page->assertPresent('#emailField')->assertPresent('#confirmPasswordField');

    $page->fill('#emailField', 'bea@example.com');
    $page->fill('#passwordField', 'Passw0rd!');
    $page->fill('#confirmPasswordField', 'Passw0rd!');
    $page->click('#submitBtn');

    $page->assertPathIs('/dashboard/home')->assertSee('Olá, bea');
});

// The page read `error` from a refusal the API has always sent as `message`, so
// every reason came out as a generic "Registo falhou."
it('shows why a registration was refused', function () {
    makeUser('alice', 'Passw0rd!', 'alice@example.com');

    $page = loginPageAsk('bea');
    $page->fill('#emailField', 'alice@example.com');
    $page->fill('#passwordField', 'Passw0rd!');
    $page->fill('#confirmPasswordField', 'Passw0rd!');
    $page->click('#submitBtn');

    $page->assertSee('This email is already taken')->assertPathIs('/auth');
});
