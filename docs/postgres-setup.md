# PostgreSQL DParranda

Neon project: silent-forest-22181101, region aws-eu-central-1, database neondb.
PostgreSQL was provisioned and the public catalog imported separately.

The production website **continues serving /events.json** until the API and protected admin console are tested.
The sync mirroring script can import the full SQLite originals, source logs, published cards and seed ads.
It does not remove original SQLite data, public JSON or manually edited ad campaigns and overrides.

To enable automatic mirroring set repository Actions secret DPARRANDA_DATABASE_URL with the Neon pooled connection URI, then run the workflow. Never commit or share credentials. The scheduled workflow will skip PostgreSQL safely when the secret is absent.

Do not expose DATABASE_URL in the frontend or prefix it with NEXT_PUBLIC_. Protect future admin endpoints with server-side authentication and roles.
