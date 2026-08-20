import { useCallback, useState } from 'react';
import { movedTo } from '../geometry';
import type { MapObject } from '../types/map';

const SHELF_LABELS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';

function shelfLabel(index: number): string {
  return index <= SHELF_LABELS.length ? SHELF_LABELS[index - 1] : String(index);
}

/** 仮 id の下書きに、同じ種別の通し番号から id と名前を与える。 */
function identify(draft: MapObject, placed: MapObject[]): MapObject {
  const order = placed.filter((object) => object.type === draft.type).length + 1;
  if (draft.type === 'shelf') {
    return { ...draft, id: `shelf-${order}`, name: `棚${shelfLabel(order)}` };
  }
  const prefix = draft.type === 'entrance' ? 'ent' : 'reg';
  return { ...draft, id: `${prefix}-${order}` };
}

export function useMapEditor() {
  const [objects, setObjects] = useState<MapObject[]>([]);

  const place = useCallback((draft: MapObject) => {
    setObjects((previous) => [...previous, identify(draft, previous)]);
  }, []);

  const move = useCallback((id: string, x: number, y: number) => {
    setObjects((previous) =>
      previous.map((object) => (object.id === id ? movedTo(object, x, y) : object)),
    );
  }, []);

  return { objects, place, move };
}
