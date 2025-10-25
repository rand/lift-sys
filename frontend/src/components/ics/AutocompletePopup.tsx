/**
 * AutocompletePopup: Popup menu for file and symbol completion
 */

import { useEffect, useState, useRef } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { AutocompleteItem } from '@/lib/ics/autocomplete';
import { cn } from '@/lib/utils';

interface AutocompletePopupProps {
  items: AutocompleteItem[];
  selected: number;
  position: { top: number; left: number };
  onSelect: (item: AutocompleteItem) => void;
  onKeyDown: (key: string) => void;
}

export function AutocompletePopup({
  items,
  selected,
  position,
  onSelect,
  onKeyDown,
}: AutocompletePopupProps) {
  const popupRef = useRef<HTMLDivElement>(null);
  const selectedRef = useRef<HTMLDivElement>(null);

  // Scroll selected item into view
  useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [selected]);

  // Listen for autocomplete keyboard events
  useEffect(() => {
    const handleKeyEvent = (event: Event) => {
      const customEvent = event as CustomEvent;
      if (customEvent.detail?.key) {
        onKeyDown(customEvent.detail.key);
      }
    };

    document.addEventListener('autocompleteKey', handleKeyEvent);
    return () => document.removeEventListener('autocompleteKey', handleKeyEvent);
  }, [onKeyDown]);

  if (items.length === 0) {
    return null;
  }

  return (
    <div
      ref={popupRef}
      className="autocomplete-popup fixed z-50 min-w-[200px] max-w-[400px]"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`,
      }}
    >
      <ScrollArea className="max-h-[300px]">
        <div className="p-1">
          {items.map((item, index) => (
            <div
              key={item.id}
              ref={index === selected ? selectedRef : null}
              className={cn(
                'autocomplete-item',
                index === selected && 'selected'
              )}
              onClick={() => onSelect(item)}
              onMouseEnter={() => {
                // Update selected index on hover (would need callback)
              }}
            >
              {item.icon && (
                <span className="autocomplete-item-icon">{item.icon}</span>
              )}
              <span className="autocomplete-item-label">{item.label}</span>
              {item.detail && (
                <span className="autocomplete-item-detail">{item.detail}</span>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
