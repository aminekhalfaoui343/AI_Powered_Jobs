# Kubernetes architecture

This folder is the Kubernetes equivalent of `docker-compose.yml`.
Compose stays for local development. Use these manifests for a cluster
(Docker Desktop Kubernetes, minikube, kind, or a remote cluster).

```text
Browser / Next.js
        │
        ▼
   Ingress (optional)
        │
        ▼
   Service/api :8000
        │
        ▼
   Deployment/api  (replicas: 2)
        │ enqueue job
        ▼
   Service/redis :6379  ←── Deployment/redis (1 replica + PVC)
        │ consume job                    (queue + live status)
        ▼
   Deployment/worker (replicas: 2, ARQ)
        │ persist result
        ▼
   Service/postgres :5432  ←── Deployment/postgres (1 replica + PVC)
```

Redis stays at one replica because it is the ARQ queue. PostgreSQL stays at
one replica because it is the durable store for extracted jobs. The API and
workers are stateless, so they can scale independently.

## 1. Build the application image

```powershell
docker build -t job-intelligence:local .
```

Load it into the cluster if the cluster cannot see your local Docker daemon:

```powershell
# minikube
minikube image load job-intelligence:local

# kind
kind load docker-image job-intelligence:local
```

Docker Desktop Kubernetes can use `imagePullPolicy: IfNotPresent` as-is.

## 2. Add secrets

Edit `k8s/secret.yaml` and set:

```yaml
OPENROUTER_API_KEY: "sk-or-..."
LANGSMITH_API_KEY: "lsv2_..."   # optional
POSTGRES_PASSWORD: "change-me"  # default in-repo value is jobintel
```

Do not commit real keys. Non-secret settings live in `k8s/configmap.yaml`.
Postgres credentials also live in `k8s/secret.yaml` (`POSTGRES_USER`,
`POSTGRES_PASSWORD`, `POSTGRES_DB`). Change the password before any shared
cluster. The API and worker build `DATABASE_URL` from those values plus
`POSTGRES_HOST=postgres` in the ConfigMap.

## 3. Deploy

```powershell
kubectl apply -k k8s/
kubectl -n job-intelligence get pods,svc
```

Wait until `api`, `worker`, `redis`, and `postgres` are Ready.

## 4. Call the API

Port-forward (simplest):

```powershell
kubectl -n job-intelligence port-forward svc/api 8000:8000
```

Then:

```powershell
curl http://localhost:8000/health
```

Point the Next.js app at that API:

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

If Ingress is installed, add `127.0.0.1 job-intelligence.local` to your hosts
file and open `http://job-intelligence.local`.

## 5. Scale workers

```powershell
kubectl -n job-intelligence scale deployment/worker --replicas=3
```

Each extra replica consumes more ARQ jobs from the same Redis queue.
Keep `postgres` and `redis` at 1 replica; they hold state.

## 6. Logs

```powershell
kubectl -n job-intelligence logs -l app.kubernetes.io/component=api --tail=50
kubectl -n job-intelligence logs -l app.kubernetes.io/component=worker -f
kubectl -n job-intelligence logs -l app.kubernetes.io/component=postgres --tail=50
```

Inspect persisted jobs after port-forward:

```powershell
curl http://localhost:8000/jobs
```

Connect to Postgres inside the cluster:

```powershell
kubectl -n job-intelligence exec -it deploy/postgres -- psql -U jobintel -d jobintel
```

## 7. Remove the stack

```powershell
kubectl delete -k k8s/
```
