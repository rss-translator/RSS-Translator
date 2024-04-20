[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/KnVkVX?referralCode=QWy2ii)

## Notes

1. If you bind a domain name, please change the value of Railway's variable `CSRF_TRUSTED_ORIGINS` to your domain name.
2. Default account: admin Default password: rsstranslator
3. Please change your password immediately after logging in.
4. Please do not change the value of the variable PORT, otherwise it may lead to inaccessibility.

## Optional variables

`HUEY_WORKERS` Adjust the number of threads, if it runs laggy, you can change it to 1, default is 10.

`default_update_frequency` Adjust the default update time (minutes), default is 30.

`default_max_posts` Adjust the default maximum number of translations per source, default is 20.
