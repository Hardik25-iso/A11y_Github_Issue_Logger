export default function Badge({ children, tone = "" }) {
  return (
    <span className={`badge${tone ? ` ${tone.toLowerCase()}` : ""}`}>
      {children}
    </span>
  );
}
