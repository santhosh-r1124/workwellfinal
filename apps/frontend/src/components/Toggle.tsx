interface ToggleProps {
  checked: boolean;
  onChange: () => void;
  label: string;
  disabled?: boolean;
}

/** The switch used for consent, notification and org-policy controls.
 *  Extracted because three copies had already drifted in their disabled
 *  and focus states, and a consent control that looks interactive while
 *  ignoring clicks is the worst version of this component to get wrong. */
export default function Toggle({ checked, onChange, label, disabled = false }: ToggleProps) {
  return (
    <button
      onClick={onChange}
      disabled={disabled}
      role="switch"
      aria-checked={checked}
      aria-label={label}
      className={`relative h-6 w-11 shrink-0 rounded-full border transition-colors
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-accent
                  disabled:opacity-40 disabled:cursor-not-allowed ${
                    checked ? "bg-accent-deep border-accent-deep" : "bg-surface-raised border-line"
                  }`}
    >
      <span
        className={`absolute top-[3px] left-[3px] h-4 w-4 rounded-full bg-white transition-transform ${
          checked ? "translate-x-5" : ""
        }`}
      />
    </button>
  );
}
