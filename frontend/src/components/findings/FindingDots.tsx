interface FindingDotsProps {
  count: number;
  activeIndex: number;
  colorFor: (index: number) => string;
  onSelect: (index: number) => void;
  labelPrefix: string;
}

/** Right-edge dot rail for jumping between cards in a scroll-stack (findings/diff screens). */
export function FindingDots({ count, activeIndex, colorFor, onSelect, labelPrefix }: FindingDotsProps) {
  return (
    <div style={{ position: "absolute", right: -30, top: "50%", transform: "translateY(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 13, zIndex: 6 }}>
      {Array.from({ length: count }, (_, i) => {
        const active = i === activeIndex;
        const color = colorFor(i);
        return (
          <button
            key={i}
            onClick={() => onSelect(i)}
            title={`${labelPrefix} ${i + 1} of ${count}`}
            style={{
              width: active ? 12 : 9,
              height: active ? 12 : 9,
              borderRadius: "50%",
              background: color,
              opacity: active ? 1 : 0.4,
              border: "none",
              padding: 0,
              cursor: "pointer",
              boxShadow: active ? `0 0 0 5px ${color}2A` : "none",
              transition: "all 0.16s cubic-bezier(0.22,1,0.36,1)",
              flexShrink: 0,
            }}
          />
        );
      })}
    </div>
  );
}
