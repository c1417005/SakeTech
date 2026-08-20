import type { MapObject, Shelf } from './types/map';

/** 配置が確定するまでの仮 id。既存オブジェクトとは決して一致しない。 */
export const DRAFT_ID = 'draft';

export type PaletteItem = {
  label: string;
  /** ドラッグを始めるたびに新しい仮オブジェクトを作る。 */
  create: () => MapObject;
};

function shelfItem(length: Shelf['length']): PaletteItem {
  return {
    label: `棚 ${length}マス`,
    create: () => ({
      type: 'shelf',
      id: DRAFT_ID,
      name: '棚',
      x: 0,
      y: 0,
      length,
      facing: 'north',
      brand_ids: [],
    }),
  };
}

export const PALETTE_ITEMS: PaletteItem[] = [
  shelfItem(2),
  shelfItem(3),
  shelfItem(4),
  { label: '出入口', create: () => ({ type: 'entrance', id: DRAFT_ID, x: 0, y: 0 }) },
  { label: 'レジ', create: () => ({ type: 'register', id: DRAFT_ID, x: 0, y: 0 }) },
];
