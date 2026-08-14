# frontend — 店員向け Web アプリ

ルートの `CLAUDE.md` を先に読むこと。ここには frontend 固有の規約だけを書く。

## スタック

- React + Vite + TypeScript
- Tailwind CSS
- 状態管理ライブラリなし（`useState` と カスタムフックで足りる）
- ドラッグ操作のライブラリなし（Pointer Events を直接使う）

```bash
npm run dev     # 開発サーバー
npm run build   # 型検査 + ビルド
```

## ディレクトリ

```
src/
  types/map.ts        API 契約の型定義。ここが単一の真実
  api/                fetch のラッパーとモック
  hooks/              useMapEditor など
  components/         UI
  App.tsx
```

## 中心となる設計

### objects 配列が唯一の真実

画面に見えているマップは `objects` 配列の描画結果にすぎない。

1. アプリは `objects: MapObject[]` を状態として持つ
2. 配列を見て描画する
3. 操作されたら配列を書き換える → 再描画される

**逆向きを絶対に作らない。** DOM 要素の位置を読み取ってデータを組み立てる処理を書いてはいけない。データが正で、画面が従。

この構造のおかげで、保存は配列をそのまま送るだけ、読み込みは受け取った配列を状態に入れるだけで済む。

### 型定義が API 契約

`src/types/map.ts` はバックエンドとの合意そのもの。**ここを変更するのは契約変更にあたる。** 実装の都合で勝手に書き換えない。

```ts
export type Facing = 'north' | 'south' | 'east' | 'west';

export type Shelf = {
  type: 'shelf';
  id: string;
  name: string;
  x: number;
  y: number;
  length: 2 | 3 | 4;
  facing: Facing;
  brand_ids: number[];
};

export type Marker = {
  type: 'entrance' | 'register';
  id: string;
  x: number;
  y: number;
};

export type MapObject = Shelf | Marker;

export type MapData = {
  grid: { width: number; height: number };
  objects: MapObject[];
};
```

## スタイリング規約

Tailwind を使う。ただし例外がある。

**動的な座標は inline style で書く。** Tailwind はソースコードを文字列として走査するため、組み立てたクラス名は生成されない。

```tsx
// 動かない。クラスが生成されない
<div className={`left-[${x * 40}px]`} />

// 正しい
<div style={{ left: x * CELL_SIZE, top: y * CELL_SIZE }} />
```

静的なスタイル（色、余白、枠線）は Tailwind、計算した位置とサイズは inline style。この使い分けを守る。

## ドラッグ実装の方針

ライブラリを入れない。マス目にスナップするだけなので、座標の割り算で足りる。

```ts
const col = Math.floor((e.clientX - rect.left) / CELL_SIZE);
const row = Math.floor((e.clientY - rect.top) / CELL_SIZE);
```

Pointer Events（`pointerdown` / `pointermove` / `pointerup`）を使う。HTML5 Drag and Drop API は使わない（挙動がブラウザ依存で、ドラッグ中のプレビュー制御が難しい）。

## UI の原則

利用者は **50〜60代の店主で、PC はメールと発注システムしか使わない**。接客のプロだが IT には不慣れ。

**守ること**

- 1 画面で完結させる。タブ、階層メニュー、モーダルの多用を避ける
- 操作しなくても最新になる。更新ボタンを押させない
- 意味は文字で書く。アイコンだけで伝えない
- クリック対象を大きく取る

**やらないこと**

- エラーコードや英語のメッセージをそのまま表示する
- 自動保存のたびにトーストを出す（うるさい。状態表示で足りる）
- 色だけで状態を区別する（必ず文字ラベルを併記）

## モックモード

**バックエンドが未完成でも動くこと。** これは任意ではなく必須要件。

環境変数 `VITE_USE_MOCK=true` のとき、`src/api/` のリクエストがモック実装に切り替わる。コンポーネント側はモックかどうかを知らない。

ハッカソン当日のデモは画面内シミュレーションで行うため、モックモードは本番経路でもある。壊さない。

## やってほしくないこと

- **ライブラリを勝手に追加しない。** 必要だと思ったら、まず理由を述べて確認を取る
- **隣接判定をフロントに書かない。** `shelf_id` はバックエンドが返す
- **`any` を使わない。** 型が分からない場合は確認する
- **チケットのスコープ外に手を出さない。** 気になる箇所を見つけたら、直さずに報告する
- **コメントで補うより、名前と型で表す。** 自明でない判断だけコメントする
