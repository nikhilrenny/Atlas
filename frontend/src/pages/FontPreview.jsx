// Temporary comparison page for the ATLAS wordmark font pick -- see £fonts.
// Loads Cinzel, Playfair Display, and Bodoni Moda from Google Fonts (none of these
// are installed app-wide yet; this page pulls its own <link> so it doesn't affect
// anything else while Nik is just looking).
export default function FontPreview() {
  return (
    <div style={{ minHeight: "100vh", padding: "3rem 1.5rem", display: "flex", flexDirection: "column", gap: "3rem" }}>
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Cinzel:wght@700;800&family=Playfair+Display:wght@700;800;900&family=Bodoni+Moda:wght@700;800;900&display=swap"
      />
      <p style={{ color: "var(--text-3)", fontSize: "0.85rem", textAlign: "center" }}>
        Temporary comparison page -- £fonts. Not part of the real UI.
      </p>

      {[
        { name: "Cinzel", family: "'Cinzel', serif", weight: 700, tracking: "0.15em" },
        { name: "Playfair Display", family: "'Playfair Display', serif", weight: 800, tracking: "0.1em" },
        { name: "Bodoni Moda", family: "'Bodoni Moda', serif", weight: 800, tracking: "0.08em" },
      ].map(f => (
        <div key={f.name} style={{ textAlign: "center" }}>
          <p style={{ color: "var(--text-2)", fontSize: "0.8rem", marginBottom: "0.75rem", fontFamily: "'JetBrains Mono', monospace" }}>
            {f.name}
          </p>
          <p
            style={{
              fontFamily: f.family,
              fontWeight: f.weight,
              fontSize: "5.5rem",
              letterSpacing: f.tracking,
              textTransform: "uppercase",
              color: "#F7F0DE",
              textShadow: "0 2px 30px rgba(30, 27, 75, 0.45), 0 1px 3px rgba(30, 27, 75, 0.35)",
              margin: 0,
              lineHeight: 1,
            }}
          >
            Atlas
          </p>
        </div>
      ))}
    </div>
  );
}
