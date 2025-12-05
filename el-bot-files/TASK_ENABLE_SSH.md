# 🔧 AGENT TASK: Enable SSH on Server

## Задача
Включить SSH сервер и настроить автозапуск.

## Команды для выполнения

```bash
# 1. Запустить SSH
sudo systemctl start ssh

# 2. Включить автозапуск
sudo systemctl enable ssh

# 3. Проверить статус
sudo systemctl status ssh

# 4. Проверить что слушает на всех интерфейсах
ss -tlnp | grep 22

# 5. Открыть порт в файрволе (если есть)
sudo ufw allow 22/tcp 2>/dev/null || echo "UFW not active"

# 6. Показать IP адреса
ip a | grep "inet "
```

## Ожидаемый результат
- SSH работает на порту 22
- Автозапуск включен
- Порт открыт в файрволе

## После завершения
Отправь статус в Telegram:

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "'"${TELEGRAM_ADMIN_ID}"'",
    "text": "✅ SSH ENABLED\n\nSSH server is now running on port 22.\nYou can connect via:\nssh flomaster@100.101.215.9"
  }'
```
