# Deploy ErrorLens Stage on k3s

## 1. Create database
```bash
psql -U postgres -h 192.168.1.74
CREATE DATABASE errorlens_stage;
\q
```

## 2. Apply manifests
```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f backend-deployment.yaml
kubectl apply -f backend-service.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f frontend-service.yaml
```

## 3. Verify
```bash
kubectl get pods -n errorlens-stage
kubectl get svc -n errorlens-stage
curl http://192.168.1.74:31200/health
curl http://192.168.1.74:31201
```

## 4. Update ConfigMap password
```bash
kubectl edit configmap errorlens-config -n errorlens-stage
# Replace your_password with actual PostgreSQL password
```

## Next: GitLab CI pipeline
