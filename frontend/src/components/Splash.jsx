import { useEffect, useState } from "react";

export default function Splash({ onDone }) {
  const [leaving, setLeaving] = useState(false);

  useEffect(() => {
    const leaveTimer = setTimeout(() => setLeaving(true), 650);
    const doneTimer = setTimeout(() => onDone(), 900);
    return () => { clearTimeout(leaveTimer); clearTimeout(doneTimer); };
  }, [onDone]);

  return (
    <div className={`splash ${leaving ? "splash-out" : ""}`}>
      <img src="/favicon.svg" alt="" className="splash-icon" />
    </div>
  );
}
