/** Luzes desfocadas no fundo: é o que dá cor ao vidro fosco por cima. */
export function Backdrop() {
  return (
    <div className="backdrop" aria-hidden="true">
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />
    </div>
  );
}
