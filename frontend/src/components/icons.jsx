/**
 * Cohesive inline-SVG icon set.
 * One visual language: 24×24 grid, 1.75 stroke, round caps/joins, currentColor.
 * Sized via the `size` prop; decorative by default (aria-hidden).
 */
function Icon({ size = 20, children, ...rest }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const CheckIcon = (props) => (
  <Icon {...props}><path d="M5 12.5l4.5 4.5L19 7" /></Icon>
);

export const ChevronDownIcon = (props) => (
  <Icon {...props}><path d="M6 9.5l6 6 6-6" /></Icon>
);

export const BoltIcon = (props) => (
  <Icon {...props}><path d="M13 2L4.5 13.5H11l-1 8.5L19.5 10H13l1-8z" /></Icon>
);

export const PlusIcon = (props) => (
  <Icon {...props}><path d="M12 5v14M5 12h14" /></Icon>
);

export const ExternalLinkIcon = (props) => (
  <Icon {...props}>
    <path d="M15 3h6v6" />
    <path d="M10 14L21 3" />
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
  </Icon>
);

export const SearchIcon = (props) => (
  <Icon {...props}><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></Icon>
);

export const CopyIcon = (props) => (
  <Icon {...props}>
    <rect x="9" y="9" width="11" height="11" rx="2" />
    <path d="M5 15V5a2 2 0 0 1 2-2h10" />
  </Icon>
);

export const SparklesIcon = (props) => (
  <Icon {...props}>
    <path d="M12 3l2 5.5L19.5 10.5 14 13l-2 5.5L10 13 4.5 10.5 10 8.5z" />
    <path d="M18.5 4v3M20 5.5h-3" />
  </Icon>
);

export const LayersIcon = (props) => (
  <Icon {...props}><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /></Icon>
);

export const EyeIcon = (props) => (
  <Icon {...props}>
    <path d="M2.5 12S6 5 12 5s9.5 7 9.5 7-3.5 7-9.5 7-9.5-7-9.5-7z" />
    <circle cx="12" cy="12" r="3" />
  </Icon>
);

export const ShieldIcon = (props) => (
  <Icon {...props}>
    <path d="M12 3l7 3v5c0 4.4-3 7.6-7 9-4-1.4-7-4.6-7-9V6z" />
    <path d="M9 12l2 2 4-4.5" />
  </Icon>
);

// Filled disc behind a check — for the success state.
export const CheckCircleIcon = ({ size = 32, ...rest }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" {...rest}>
    <circle cx="12" cy="12" r="11" fill="currentColor" opacity=".15" />
    <path d="M7.5 12.5l3 3 6-6.5" stroke="currentColor" strokeWidth="1.75"
      strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
