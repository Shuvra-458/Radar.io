import { useState } from "react";

interface Props {
  onSubmit: (company: string) => void;
  disabled: boolean;
}

export function SearchBox({ onSubmit, disabled }: Props) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed && !disabled) onSubmit(trimmed);
  };

  return (
    <form className="search-box" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Enter a company name (e.g. Stripe, Flipkart, Notion)"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        autoFocus
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        {disabled ? "Analyzing…" : "Analyze"}
      </button>
    </form>
  );
}