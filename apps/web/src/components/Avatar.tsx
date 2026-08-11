// Monogram avatar with a gradient ring — a deliberate, honest stand-in for a photo.

interface Props {
  size?: number;
  initials?: string;
}

export function Avatar({ size = 44, initials = 'MA' }: Props) {
  return (
    <div
      className="accent-gradient grid shrink-0 place-items-center rounded-2xl font-semibold text-white shadow-lg"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        boxShadow: '0 8px 24px -10px rgb(var(--glow) / 0.8)',
      }}
      aria-hidden
    >
      {initials}
    </div>
  );
}
