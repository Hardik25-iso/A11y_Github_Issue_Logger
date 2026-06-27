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

// Filled disc behind a check — for the success state.
export const CheckCircleIcon = ({ size = 32, ...rest }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" {...rest}>
    <circle cx="12" cy="12" r="11" fill="currentColor" opacity=".15" />
    <path d="M7.5 12.5l3 3 6-6.5" stroke="currentColor" strokeWidth="1.75"
      strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
