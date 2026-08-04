import type { CSSProperties } from "react";

interface IconProps {
  size?: number;
  color?: string;
  style?: CSSProperties;
}

export function ShieldIcon({ size = 24, color = "#000000", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  );
}

export function FileIcon({ size = 14, color = "rgba(255,255,255,0.5)", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M6.5 3h7l4 4v13a1 1 0 0 1-1 1h-10a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
      <path d="M13.5 3v4h4" />
    </svg>
  );
}

export function PlusIcon({ size = 20, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" style={style}>
      <path d="M12 5.5v13M5.5 12h13" />
    </svg>
  );
}

export function ScopeShieldIcon({ size = 16, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M12 21s7-3.5 7-9V5.5l-7-2.5-7 2.5V12c0 5.5 7 9 7 9z" />
    </svg>
  );
}

export function ChevronDownIcon({ size = 14, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M6 9.5l6 6 6-6" />
    </svg>
  );
}

export function ArrowUpIcon({ size = 20, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M12 19V5" />
      <path d="M5.5 11.5L12 5l6.5 6.5" />
    </svg>
  );
}

export function GithubIcon({ size = 21, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" stroke="none" style={style}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.09 3.29 9.4 7.86 10.93.57.1.79-.25.79-.55 0-.27-.01-1.16-.02-2.11-3.2.7-3.87-1.36-3.87-1.36-.53-1.33-1.29-1.69-1.29-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.25.45-2.28 1.18-3.08-.12-.29-.51-1.46.11-3.04 0 0 .96-.31 3.15 1.18a10.9 10.9 0 0 1 5.73 0c2.19-1.49 3.15-1.18 3.15-1.18.62 1.58.23 2.75.11 3.04.74.8 1.18 1.83 1.18 3.08 0 4.41-2.69 5.38-5.26 5.67.42.36.78 1.06.78 2.15 0 1.55-.01 2.8-.01 3.18 0 .3.21.66.8.55A11.51 11.51 0 0 0 23.5 12c0-6.35-5.15-11.5-11.5-11.5z" />
    </svg>
  );
}

export function PasteIcon({ size = 21, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <rect x="6" y="4" width="12" height="16" rx="3" />
      <path d="M9.5 4.5h5" />
    </svg>
  );
}

export function CheckIcon({ size = 13, color = "#04120F", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M4.5 12.5l5 5L19.5 7" />
    </svg>
  );
}

export function CheckThinIcon({ size = 16, color = "#35E0C8", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M4.5 12.5l5 5L19.5 7" />
    </svg>
  );
}

export function InfoIcon({ size = 16, color = "rgba(255,255,255,0.4)", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5.2" />
      <path d="M12 8h.01" />
    </svg>
  );
}

export function LockIcon({ size = 14, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.45)" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <rect x="5.5" y="11" width="13" height="9.5" rx="3" />
      <path d="M8.5 11V7.8a3.5 3.5 0 0 1 7 0V11" />
    </svg>
  );
}

export function WarningIcon({ size = 19, color = "#FF8B7C", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M12 4.5l8.5 15h-17l8.5-15z" />
      <path d="M12 10v4" />
      <path d="M12 17h.01" />
    </svg>
  );
}

export function SpinnerIcon({ size = 30, color = "#35E0C8", style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2.2} strokeLinecap="round" style={{ animation: "vc-spin 0.8s linear infinite", ...style }}>
      <circle cx="12" cy="12" r="9" opacity={0.2} />
      <path d="M21 12a9 9 0 0 0-9-9" />
    </svg>
  );
}

export function ConnectIcon({ size = 17, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M10 14a4 4 0 0 0 6 0l2.5-2.5a4 4 0 0 0-5.6-5.6L11.5 7.3" />
      <path d="M14 10a4 4 0 0 0-6 0L5.5 12.5a4 4 0 0 0 5.6 5.6L12.5 16.7" />
    </svg>
  );
}

export function PipelineIcon({ size = 17, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M15.8 15.8L20 20" />
    </svg>
  );
}

export function ApproveIcon({ size = 17, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M8.3 12.3l2.4 2.4 5-5.4" />
    </svg>
  );
}

export function ImplementIcon({ size = 17, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d="M14.7 6.3a3.5 3.5 0 0 0-4.7 4.7L4.5 16.5l3 3L13 14a3.5 3.5 0 0 0 4.7-4.7l-2.3 2.3-2-2z" />
    </svg>
  );
}

export function DiffIcon({ size = 17, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <rect x="4" y="4.5" width="7" height="15" rx="2" />
      <rect x="13" y="4.5" width="7" height="15" rx="2" />
    </svg>
  );
}

export function CheckCircleFilledIcon({ size = 17, style }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#35E0C8" stroke="none" style={style}>
      <circle cx="12" cy="12" r="9" />
      <path d="M8 12.2l2.6 2.6L16.5 9" stroke="#04120F" strokeWidth={2.6} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
