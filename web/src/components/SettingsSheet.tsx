import { useEffect, useRef, useState } from "react";
import { loadThemePref, setThemePref, type ThemePref } from "../lib/theme";
import { SegmentedControl } from "./SegmentedControl";

interface SettingsSheetProps {
  open: boolean;
  onClose: () => void;
  showLogout: boolean;
  onLogout: () => void;
}

/** Folha de ajustes que sobe de baixo, no estilo iOS. Usa <dialog>: fecha com Esc e prende o foco. */
export function SettingsSheet({ open, onClose, showLogout, onLogout }: SettingsSheetProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [theme, setTheme] = useState<ThemePref>(loadThemePref);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  function changeTheme(value: ThemePref) {
    setTheme(value);
    setThemePref(value);
  }

  return (
    <dialog
      ref={dialogRef}
      className="sheet glass"
      aria-labelledby="settings-title"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === dialogRef.current) onClose(); // toque fora da folha fecha
      }}
    >
      <div className="sheet-handle" aria-hidden="true" />
      <div className="sheet-head">
        <h2 id="settings-title">Ajustes</h2>
        <button type="button" className="small" onClick={onClose}>
          OK
        </button>
      </div>

      <h3 className="section-header">Aparência</h3>
      <SegmentedControl
        label="Aparência"
        value={theme}
        onChange={changeTheme}
        options={[
          { value: "system", label: "Automático" },
          { value: "light", label: "Claro" },
          { value: "dark", label: "Escuro" },
        ]}
      />
      <p className="footnote sheet-hint">Automático segue o tema do seu celular ou computador.</p>

      {showLogout && (
        <button type="button" className="destructive-text" onClick={onLogout}>
          Sair
        </button>
      )}
    </dialog>
  );
}
