import { GRID_HEIGHT, GRID_WIDTH } from './constants';
import type { MapObject, Shelf } from './types/map';

export type Cell = { x: number; y: number };

/** north / south の棚は x 方向、east / west の棚は y 方向に伸びる（API 契約）。 */
function isHorizontal(shelf: Shelf): boolean {
  return shelf.facing === 'north' || shelf.facing === 'south';
}

export function objectSpan(object: MapObject): { cols: number; rows: number } {
  if (object.type !== 'shelf') return { cols: 1, rows: 1 };
  return isHorizontal(object)
    ? { cols: object.length, rows: 1 }
    : { cols: 1, rows: object.length };
}

export function occupiedCells(object: MapObject): Cell[] {
  const { cols, rows } = objectSpan(object);
  const cells: Cell[] = [];
  for (let dy = 0; dy < rows; dy++) {
    for (let dx = 0; dx < cols; dx++) {
      cells.push({ x: object.x + dx, y: object.y + dy });
    }
  }
  return cells;
}

function isWithinGrid(object: MapObject): boolean {
  return occupiedCells(object).every(
    (cell) => cell.x >= 0 && cell.x < GRID_WIDTH && cell.y >= 0 && cell.y < GRID_HEIGHT,
  );
}

function overlaps(a: MapObject, b: MapObject): boolean {
  const cellsOfB = occupiedCells(b);
  return occupiedCells(a).some((cell) =>
    cellsOfB.some((other) => other.x === cell.x && other.y === cell.y),
  );
}

/** 同じ id のものは自分自身なので無視する。移動中のオブジェクトが自分と衝突しない。 */
export function canPlace(target: MapObject, objects: MapObject[]): boolean {
  return (
    isWithinGrid(target) &&
    objects.every((object) => object.id === target.id || !overlaps(target, object))
  );
}

export function movedTo(object: MapObject, x: number, y: number): MapObject {
  return object.type === 'shelf' ? { ...object, x, y } : { ...object, x, y };
}
