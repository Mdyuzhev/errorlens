# 🔍 AGENT TASK: Ping All Services

## Цель
Проверить доступность всех сервисов на домашнем сервере.

---

## Проверки

```bash
# K8s pods
kubectl get pods -A | grep -v Completed

# Docker containers
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Основные порты (используй IP хоста, не localhost!)
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.74:8080   # GitLab (302=OK)
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.74:8088   # YouTrack (200=OK)
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.74:30300  # Grafana NodePort (302=OK)

# Результат
echo "Done"
```

---

## Ожидаемый результат
Таблица со статусами всех сервисов.
