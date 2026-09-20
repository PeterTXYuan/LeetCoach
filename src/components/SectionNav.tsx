import { useRef } from "react";

export type SectionId = "coach" | "practice" | "progress" | "about";
export type SectionOption = { id: SectionId; label: string };

type SectionNavProps = {
  sections: readonly SectionOption[];
  activeSection: SectionId;
  onSelect: (section: SectionId) => void;
};

export function SectionNav({ sections, activeSection, onSelect }: SectionNavProps) {
  const buttons = useRef<Partial<Record<SectionId, HTMLButtonElement | null>>>({});

  return (
    <nav aria-label="LeetCoach sections">
      <div className="section-nav" role="tablist" aria-label="Sections">
        {sections.map((section, index) => (
          <button
            key={section.id}
            ref={(element) => { buttons.current[section.id] = element; }}
            id={`section-tab-${section.id}`}
            className="section-nav-option"
            type="button"
            role="tab"
            aria-selected={activeSection === section.id}
            aria-controls={`section-panel-${section.id}`}
            tabIndex={activeSection === section.id ? 0 : -1}
            onClick={() => onSelect(section.id)}
            onKeyDown={(event) => {
              let nextIndex: number;
              switch (event.key) {
                case "ArrowRight": nextIndex = (index + 1) % sections.length; break;
                case "ArrowLeft": nextIndex = (index - 1 + sections.length) % sections.length; break;
                case "Home": nextIndex = 0; break;
                case "End": nextIndex = sections.length - 1; break;
                default: return;
              }
              event.preventDefault();
              const next = sections[nextIndex].id;
              onSelect(next);
              buttons.current[next]?.focus();
            }}
          >
            {section.label}
          </button>
        ))}
      </div>
    </nav>
  );
}
