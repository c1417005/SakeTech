// バックエンドとの API 契約そのもの。実装の都合で書き換えない。

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
