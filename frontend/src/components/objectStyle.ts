import type { MapObject } from '../types/map';

export const OBJECT_COLOR: Record<MapObject['type'], string> = {
  shelf: 'bg-amber-700 border-amber-900',
  entrance: 'bg-emerald-600 border-emerald-800',
  register: 'bg-sky-700 border-sky-900',
};

export function objectLabel(object: MapObject): string {
  if (object.type === 'shelf') return object.name;
  return object.type === 'entrance' ? '出入口' : 'レジ';
}
