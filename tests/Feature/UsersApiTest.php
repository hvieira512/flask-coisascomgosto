<?php

beforeEach(fn () => signIn());

describe('listing', function () {
    it('lists only the signed-in owner at first', function () {
        $body = $this->getJson('/api/users/')->json();

        expect(array_column($body['users'], 'username'))->toBe(['tokenuser'])
            ->and($body['pagination']['total'])->toBe(1);
    });

    it('lists registered users', function () {
        makeUser('alice');
        makeUser('bob');

        $body = $this->getJson('/api/users/')->json();
        expect(array_column($body['users'], 'username'))->toContain('alice')
            ->and($body['pagination']['total'])->toBe(3);
    });

    it('never lists the password', function () {
        makeUser('alice');

        foreach ($this->getJson('/api/users/')->json('users') as $user) {
            expect($user)->not->toHaveKey('password');
        }
    });

    it('pages', function () {
        foreach (['alice', 'bob', 'carol'] as $name) {
            makeUser($name);
        }

        $body = $this->getJson('/api/users/?page=2&limit=2')->json();
        expect($body['users'])->toHaveCount(2)
            ->and($body['pagination']['page'])->toBe(2);
    });

    it('refuses nonsense paging with 400', function () {
        $this->getJson('/api/users/?limit=0')->assertStatus(400);
    });
});

describe('reading one', function () {
    it('returns it', function () {
        $user = makeUser('alice');

        $this->getJson("/api/users/{$user->id}")->assertOk()->assertJsonPath('username', 'alice');
    });

    it('never returns the password', function () {
        $user = makeUser('alice');

        expect($this->getJson("/api/users/{$user->id}")->json())->not->toHaveKey('password');
    });

    it('answers 404 for an unknown id', function () {
        $this->getJson('/api/users/9999')->assertNotFound();
    });
});
