# Reliability notes

## Timeout

`LLM_JOB_TIMEOUT = 60` prevents a single LLM inference call from hanging forever. In a real service, a stuck provider call can block a worker and delay the queue. A 60-second timeout means the job is failed or retried quickly instead of consuming resources indefinitely.

## Retry

`LLM_MAX_TRIES = 3` allows the worker to retry temporary issues such as network blips, provider timeouts, malformed JSON, or 429/5xx responses. The job is not retried forever; it stops after the configured limit and surfaces a clear failure.

## Concurrency

`LLM_MAX_CONCURRENT = 5` limits how many LLM calls can run at the same time inside each worker process. This prevents the app from overwhelming OpenRouter's rate limits and keeps the queue responsive.

## Async workers, Redis, and ARQ

- Asynchronous execution means the API can return promptly after enqueuing work.
- Concurrency is the number of tasks running in parallel at once.
- Timeout is the maximum time one task is allowed to run.
- Retries are repeated attempts after a temporary failure.
- Redis stores the queued jobs and their live status.
- PostgreSQL stores extracted job results after the worker finishes, so listings survive Redis restarts.
- ARQ is the worker system that consumes queue jobs and runs the application logic.

Together, the pattern is:

Client -> FastAPI -> Redis queue -> ARQ worker -> extract -> PostgreSQL
                                              ↘ Redis (live job status)

## Multi-source discovery

Discovery is registry-based and runs source adapters concurrently:

```text
POST /jobs/search -> source registry -> parallel discovery -> URL/metadata dedupe
				  -> ARQ process_job -> source scraper -> LLM extraction
```

The source registry contains France Travail, Indeed, HelloWork, Welcome to the
Jungle, JobTeaser, and APEC. France Travail is the active adapter. Indeed is
registered behind an approved-provider boundary but remains unavailable until
this project has an approved Indeed API or partner integration. The platform
does not scrape Indeed's public site or bypass CAPTCHAs, authentication, robots
restrictions, or anti-bot controls.

Any future provider must be obtained through Indeed's official developer
portal and used under the applicable API terms: https://developer.indeed.com/.

Set enabled sources through the environment without changing code:

```dotenv
JOB_SOURCES_ENABLED=france_travail
```

France Travail discovery reads publicly accessible listing links from its job
search page and does not require API credentials. The adapter only discovers
public detail-page URLs; it does not sign in or bypass access controls. Search
availability and result parsing depend on the public page and may change if its
markup changes.

To enable Indeed later, an approved provider must be implemented and injected
into `IndeedSearchAdapter`; adding `indeed` to this setting alone is not
sufficient and will not make public-site scraping available.

Use `sources: ["all"]` to query every configured source. `POST /jobs/search`
returns a `sources` object with per-source status and job counts, while
`GET /sources` exposes source names, enabled state, and access classification.
One source failure is isolated from the others. Duplicate listings are merged
by normalized URL or matching title, company, and location, and the merged
listing retains all source IDs.

The API does not wait for the expensive LLM call. It only enqueues the job and returns a `job_id`.

This is why the sentence below is technically accurate:

> "I use asynchronous workers so the API isn't blocked by expensive LLM extraction. Redis acts as the queue, while ARQ controls execution, retries and concurrency."

The API remains non-blocking because queueing is fast, while the expensive work runs later in an async worker process.

## Running with Docker Compose

```bash
docker compose build
docker compose up
```

Check container status:

```bash
docker compose ps
```

Useful logs:

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f redis
docker compose logs -f postgres
```

Stop everything:

```bash
docker compose down
```

Delete Redis data volumes as well:

```bash
docker compose down -v
```

### Troubleshooting

- Port 8000 already in use: change the host mapping in `docker-compose.yml`.
- Redis connection refused: check the Redis service name (`redis`) and the `REDIS_DSN` value.
- PostgreSQL connection refused: check the Postgres service name (`postgres`) and `POSTGRES_HOST`.
- Worker cannot reach Redis: ensure the worker uses `redis://redis:6379` instead of `localhost`.
- API works but jobs do not execute: inspect the worker container logs and ARQ configuration.
- OpenRouter / LLM authentication failure: verify the environment variable is set and not printed into logs.

### Docker networking note

Inside Docker Compose, `localhost` means the current container. To reach Redis from the API or worker, the correct target is the Compose service name: `redis`. To reach PostgreSQL, use `postgres`.

This is why the app uses `redis://redis:6379` and `POSTGRES_HOST=postgres` inside containers instead of `localhost`.
"# AI_Powered_Jobs" 
