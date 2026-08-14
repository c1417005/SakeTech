import { CELL_SIZE } from '../constants';
import { objectSpan } from '../geometry';
import type { MapObject } from '../types/map';
import { OBJECT_COLOR, objectLabel } from './objectStyle';

type Appearance = 'placed' | 'moving' | 'preview-ok' | 'preview-ng';

const APPEARANCE_CLASS: Record<Appearance, string> = {
  placed: 'cursor-grab active:cursor-grabbing',
  moving: 'opacity-30',
  'preview-ok': 'opacity-80 ring-4 ring-emerald-400',
  'preview-ng': 'opacity-80 ring-4 ring-red-600',
};

type PlacedObjectProps = {
  object: MapObject;
  appearance: Appearance;
  onPointerDown?: (event: React.PointerEvent) => void;
};

export function PlacedObject({ object, appearance, onPointerDown }: PlacedObjectProps) {
  const span = objectSpan(object);
  const color =
    appearance === 'preview-ng' ? 'bg-red-600 border-red-800' : OBJECT_COLOR[object.type];

  return (
    <div
      onPointerDown={onPointerDown}
      className={`absolute flex touch-none select-none items-center justify-center rounded border-2 text-sm font-bold text-white ${color} ${APPEARANCE_CLASS[appearance]}`}
      style={{
        left: object.x * CELL_SIZE,
        top: object.y * CELL_SIZE,
        width: span.cols * CELL_SIZE,
        height: span.rows * CELL_SIZE,
      }}
    >
      {objectLabel(object)}
      {appearance === 'preview-ng' && (
        <span className="absolute -top-7 left-0 whitespace-nowrap rounded bg-red-700 px-2 py-0.5 text-xs font-bold text-white">
          置けません
        </span>
      )}
    </div>
  );
}
