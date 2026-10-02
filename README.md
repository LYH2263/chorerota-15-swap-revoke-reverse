# Chorerota · 家庭值日轮转

底座：成员+任务 → round-robin 生成周表 → 申请对调 → 确认改表 → 已确认可撤销回滚（status=revoked）。

撤销取舍：后续已确认对调动过同一格时撤销**失败**（409 `slot_touched:<ids>`，不做级联），按提示先撤阻塞单（LIFO）。错误码契约：`not_confirmed`(400) / `slot_touched:<ids>`(409) / `slot_missing`(400) / `swap_not_found`(404)，前端 `src/swapErrors.js` 按同一套码出文案。列表默认隐藏已撤销（`GET /api/swaps?include_revoked=1` 全开），详情 `GET /api/swaps/{id}` 不受过滤影响。

| 服务 | 端口 |
| --- | --- |
| 前端 | 5100 |
| API | 10100 |

```bash
docker compose up --build
pytest backend/app/tests
```

种子含 clean/dirty。0-1 空桩：`streak_badge` / `skip_week` / `chore_photo`。
