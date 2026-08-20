import { objectSpan } from '../geometry';
import { PALETTE_ITEMS } from '../palette';
import type { MapObject } from '../types/map';
import { OBJECT_COLOR } from './objectStyle';

const SWATCH_CELL = 16;

type PaletteProps = {
  onPickUp: (event: React.PointerEvent, draft: MapObject) => void;
};

export function Palette({ onPickUp }: PaletteProps) {
  return (
    <section className="w-60 shrink-0">
      <h2 className="mb-1 text-lg font-bold text-zinc-800">置くもの</h2>
      <p className="mb-3 text-sm text-zinc-600">右の方眼へドラッグしてください</p>
      <ul className="flex flex-col gap-3">
        {PALETTE_ITEMS.map((item) => {
          const sample = item.create();
          const span = objectSpan(sample);
          return (
            <li key={item.label}>
              <div
                onPointerDown={(event) => onPickUp(event, item.create())}
                className="flex cursor-grab touch-none select-none items-center gap-3 rounded-lg border-2 border-zinc-300 bg-white px-3 py-4 active:cursor-grabbing"
              >
                <span
                  className={`shrink-0 rounded border-2 ${OBJECT_COLOR[sample.type]}`}
                  style={{ width: span.cols * SWATCH_CELL, height: span.rows * SWATCH_CELL }}
                />
                <span className="text-base font-bold text-zinc-800">{item.label}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
