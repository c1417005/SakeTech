# KUMU backend

FastAPI + numpy + SQLite。facing 隣接判定・滞留(state)・好み推定・さけのわ取得を担う。
データフロー: iOS `POST /ingest` → サーバー → `GET /sessions` → 店員Web。

## セットアップ & 起動
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m app.seed_demo          # さけのわ石川銘柄を取得＋デモ店マップを投入
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# docs: http://localhost:8000/docs
```
`0.0.0.0` バインドで同一LANの iOS から到達可能に。

## デモ / モック再生（当日の本番経路）
```
GET http://localhost:8000/sessions?mock=true   # 入店->1-3番棚->4番で迷う を再生
```
実 API が落ちてもこれでデモ継続可。`KUMU_MOCK=true` でも有効化。

## テスト
```bash
python tests/test_geometry_inference.py   # facing判定 / type4 / 推定（ネットワーク不要）
python tests/test_api.py                  # API e2e（銘柄はseedするのでネットワーク不要）
```

## 主なエンドポイント
| Method | Path | 用途 |
|---|---|---|
| POST/GET | `/map` | マップ保存/読み戻し（`frontend/src/types/map.ts` と同形） |
| GET | `/sessions` | 来店者。`?mock=true` でデモ再生 |
| POST | `/ingest` | iOS からの検出投入 |
| GET | `/brands`, `/brands/{id}` | 石川県の銘柄（棚詳細用） |
| GET | `/attribution` | さけのわ帰属表示 |
| POST | `/admin/sync-sakenowa` | さけのわ再取得 |

詳細: `../docs/api-contract.md`, `../docs/backend-design.md`。
