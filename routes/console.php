<?php

use App\Models\User;
use App\Support\Uploads;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;

/*
 * The only thing in the project that deletes a photograph. Removing one in the
 * dashboard marks its row; deleting a piece or a colour removes rows and leaves
 * the files, because the owners' only copy of a photograph may be the one they
 * uploaded. Run it by hand, or from cron; nothing calls it automatically.
 */
Artisan::command('app:sweep-uploads {--days=30 : How long a file must have been unreferenced} {--dry-run : List what would go, delete nothing}', function () {
    $days = (int) $this->option('days');
    $dryRun = (bool) $this->option('dry-run');

    // Inclusive: DATETIME keeps whole seconds, so --days=0 must still reach a
    // row marked in the current second.
    $purged = $dryRun ? 0 : DB::table('product_images')
        ->whereNotNull('deleted_at')
        ->whereRaw('deleted_at <= NOW() - INTERVAL ? DAY', [$days])
        ->delete();

    // Removed photographs included: they are restorable, so still in use.
    $referenced = DB::table('product_images')->pluck('url')
        ->merge(DB::table('collections')->whereNotNull('image_url')->pluck('image_url'))
        ->all();

    $removed = Uploads::sweep($referenced, $days, $dryRun);

    foreach ($removed as $url) {
        $this->line(($dryRun ? 'would remove ' : 'removed ').$url);
    }
    $this->info($dryRun
        ? count($removed).' file(s) would go; nothing was changed.'
        : "Rows purged: {$purged}. Files removed: ".count($removed).'.');
})->purpose('Delete uploaded files no row points at any more');

/*
 * There is one kind of account: everyone who can sign in can do everything.
 * The password is prompted for, so it stays out of the shell history.
 */
Artisan::command('app:create-user {username}', function (string $username) {
    $email = $this->ask('E-mail (used for the account only; nothing is sent)');
    $password = $this->secret('Password');

    if ($password !== $this->secret('Repeat the password')) {
        $this->fail('The passwords do not match.');
    }
    if (User::where('username', $username)->exists()) {
        $this->fail("The username {$username} is already taken.");
    }
    if (User::where('email', $email)->exists()) {
        $this->fail("The e-mail {$email} is already taken.");
    }

    User::create(['username' => $username, 'email' => $email, 'password' => Hash::make($password)]);
    $this->info("Account created: {$username}");
})->purpose('Create an account for the dashboard');
