# KUMU API 契約 v0.1（backend ⇄ frontend / iOS）

> W1 最優先の成果物。`GET /sessions` の形をここで確定する。フロントの
> `frontend/src/types/map.ts`（＝マップ契約の正）と齟齬なく噛み合わせる。

Base URL: バックエンドのルート（例 `http://<host>:8000`）。OpenAPI/Swagger は
`/docs`。全エンドポイントはプレフィックスなし（`/map`, `/sessions`, ...）。

---

## 1. POST /map — マップ保存

Body = `MapData`（`frontend/src/types/map.ts` と同形。**この形は変えない**）。

```json
{
  "grid": { "width": 10, "height": 8 },
  "objects": [
    { "type": "shelf", "id": "shelf-a", "name": "棚A",
      "x": 2, "y": 1, "length": 3, "facing": "north", "brand_ids": [1234, 5678] },
    { "type": "entrance", "id": "ent-1", "x": 0, "y": 7 },
    { "type": "register", "id": "reg-1", "x": 9, "y": 7 }
  ]
}
```

- レスポンス: `{ "saved": true }` / 不正なら **400**（`{detail}`、コード数字は出さない方針はフロント側で吸収）
- `facing` が north/south なら x 方向、east/west なら y 方向に `length` 伸長
- entrance / register は 1 セル固定（`length`/`facing` を持たない）

## 2. GET /map — 読み戻し

POST と同形の `MapData` を返す。**未登録なら空**（エラーにしない）:
`{ "grid": {"width":10,"height":8}, "objects": [] }`。

---

## 3. GET /sessions — 来店者リスト（フロントが10秒ポーリング）★確定

`Session[]` を返す。**基本フィールド（拘束契約）** と **追加の任意フィールド** の2層。

```json
[
  {
    "session_id": "a1b2",
    "x": 6, "y": 4,
    "state": "hesitating",
    "dwell_sec": 22,
    "shelf_id": "shelf-4",

    "elapsed_sec": 40,
    "appearance_tags": ["赤の服"],
    "profile": {
      "tags": ["甘口寄り", "芳醇"],
      "confidence": "high",
      "basis": ["天狗舞", "菊姫", "手取川"]
    }
  }
]
```

### 基本フィールド（CLAUDE.md / map-spec / frontend T-07 と一致・必須）
| field | 型 | 意味 |
|---|---|---|
| `session_id` | string | 匿名の来店セッション（退店で消滅） |
| `x`, `y` | int | セル座標（整数） |
| `state` | `moving`｜`viewing`｜`hesitating` | 状態 |
| `dwell_sec` | int | 現在の棚前の滞留秒 |
| `shelf_id` | string｜null | **バックエンドが facing 隣接判定した結果**。フロントは再計算しない |

### 追加の任意フィールド（PRD F-3 / 顧客識別doc・客カード用）
| field | 型 | 意味 |
|---|---|---|
| `elapsed_sec` | int | 入店からの経過秒 |
| `appearance_tags` | string[] | 見た目タグ（服の色など・観測値） |
| `profile` | object｜null | 好み推定 |
| `profile.tags` | string[] | 平易語タグ（確信度順・最大3） |
| `profile.confidence` | `low`｜`medium`｜`high` | 確信度（low は「推定中」表示に） |
| `profile.basis` | string[] | 根拠の銘柄名（最大3） |

> [!important] 2つの版の統合について（要人間確認）
> CLAUDE.md の `GET /sessions` は基本フィールドのみ、顧客識別doc は `profile` 入り。
> ここでは **基本フィールドを厳守しつつ profile 等を追加（additive）** した。追加分は
> フロント T-07 の基本描画では無視され、客カード（F-3）実装時に消費される。
> **既存契約を壊す変更ではない**が、「profile を /sessions に載せる vs 別エンドポイント
> にする」の最終判断は人間の合意事項として残す（CLAUDE.md「契約を勝手に変えない」）。

---

## 4. POST /ingest — iOS → backend（本リポジトリが所有）

iOS が正規化座標＋服装タグを送る。サーバーがグリッドへ写像し session を更新。

```json
{ "camera_id": "cam-1",
  "detections": [ { "track_id": 1, "x": 0.6, "y": 0.5, "t": 1734250000.0,
                    "appearance_tags": ["赤の服"] } ] }
```
- `x, y`: 正規化画像座標(0..1)、足元。サーバーがグリッドセルへ写像
  （MVP=グリッド寸法でスケール。将来ホモグラフィ校正に差し替え。[TBD]）
- レスポンス: `{ "accepted": n }`

## 5. 銘柄（さけのわ / 石川県）

| Method | Path | 用途 |
|---|---|---|
| GET | `/brands` | 石川県の銘柄一覧。`?q=名前` 部分一致、`?ids=469,470` 指定取得（棚詳細 F-4） |
| GET | `/brands/{id}` | 銘柄単体 |
| GET | `/attribution` | さけのわ帰属表示テキスト（画面常設・必須） |
| POST | `/admin/sync-sakenowa` | さけのわ取得→SQLiteキャッシュ（`?force=true`） |

`Brand` = `{ brand_id, name, brewery, area, f1..f6, type4, easy_tags[], has_flavor }`。
`has_flavor=false` の欠損銘柄は `type4`/`f*`/`easy_tags` が空 → **銘柄名のみ表示**。

---

権威型定義: `backend/app/models.py`。マップ契約の正: `frontend/src/types/map.ts`。
