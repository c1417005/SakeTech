import { useCallback, useEffect, useRef, useState } from 'react';
import { CELL_SIZE } from '../constants';
import { canPlace, movedTo, type Cell } from '../geometry';
import type { MapObject } from '../types/map';

type Params = {
  objects: MapObject[];
  place: (draft: MapObject) => void;
  move: (id: string, x: number, y: number) => void;
};

export type PlacementPreview = {
  object: MapObject;
  valid: boolean;
};

type Drag = {
  /** 追従中の姿。x, y は置こうとしている候補位置。 */
  object: MapObject;
  /** パレットから出した新しいものか、方眼の上のものを動かしているか。 */
  from: 'palette' | 'grid';
  /** つかんだセルの、オブジェクト起点からのずれ。 */
  grab: Cell;
  overGrid: boolean;
  valid: boolean;
};

function cellAt(rect: DOMRect, clientX: number, clientY: number): Cell {
  return {
    x: Math.floor((clientX - rect.left) / CELL_SIZE),
    y: Math.floor((clientY - rect.top) / CELL_SIZE),
  };
}

export function useObjectDrag({ objects, place, move }: Params) {
  const gridRef = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<Drag | null>(null);
  // window のリスナーから最新の drag を読むための写し。
  const dragRef = useRef<Drag | null>(null);

  const updateDrag = useCallback((next: Drag | null) => {
    dragRef.current = next;
    setDrag(next);
  }, []);

  const follow = useCallback(
    (current: Drag, clientX: number, clientY: number): Drag => {
      const rect = gridRef.current?.getBoundingClientRect();
      if (!rect) return { ...current, overGrid: false, valid: false };

      const overGrid =
        clientX >= rect.left && clientX < rect.right && clientY >= rect.top && clientY < rect.bottom;
      const cell = cellAt(rect, clientX, clientY);
      const object = movedTo(current.object, cell.x - current.grab.x, cell.y - current.grab.y);

      return { ...current, object, overGrid, valid: overGrid && canPlace(object, objects) };
    },
    [objects],
  );

  const startPlacing = useCallback(
    (event: React.PointerEvent, draft: MapObject) => {
      event.preventDefault();
      const start: Drag = {
        object: draft,
        from: 'palette',
        grab: { x: 0, y: 0 },
        overGrid: false,
        valid: false,
      };
      updateDrag(follow(start, event.clientX, event.clientY));
    },
    [follow, updateDrag],
  );

  const startMoving = useCallback(
    (event: React.PointerEvent, object: MapObject) => {
      event.preventDefault();
      const rect = gridRef.current?.getBoundingClientRect();
      const cell = rect ? cellAt(rect, event.clientX, event.clientY) : { x: object.x, y: object.y };
      const start: Drag = {
        object,
        from: 'grid',
        grab: { x: cell.x - object.x, y: cell.y - object.y },
        overGrid: true,
        valid: true,
      };
      updateDrag(follow(start, event.clientX, event.clientY));
    },
    [follow, updateDrag],
  );

  const dragging = drag !== null;

  useEffect(() => {
    if (!dragging) return;

    const handleMove = (event: PointerEvent) => {
      const current = dragRef.current;
      if (!current) return;
      updateDrag(follow(current, event.clientX, event.clientY));
    };

    const finish = (commit: boolean) => {
      const current = dragRef.current;
      updateDrag(null);
      if (!current || !commit || !current.valid) return;
      if (current.from === 'palette') {
        place(current.object);
      } else {
        move(current.object.id, current.object.x, current.object.y);
      }
    };

    const handleUp = () => finish(true);
    const handleCancel = () => finish(false);

    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    window.addEventListener('pointercancel', handleCancel);
    window.addEventListener('blur', handleCancel);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
      window.removeEventListener('pointercancel', handleCancel);
      window.removeEventListener('blur', handleCancel);
    };
  }, [dragging, follow, updateDrag, place, move]);

  const preview: PlacementPreview | null =
    drag && drag.overGrid ? { object: drag.object, valid: drag.valid } : null;

  return {
    gridRef,
    preview,
    /** 移動中のオブジェクト。元の場所は薄く表示する。 */
    movingId: drag?.from === 'grid' ? drag.object.id : null,
    startPlacing,
    startMoving,
  };
}
