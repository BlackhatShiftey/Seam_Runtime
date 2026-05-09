export default function Spinner() {
  return (
    <div
      style={{
        width: 16,
        height: 16,
        border: '2px solid rgba(79,140,251,0.2)',
        borderTop: '2px solid #4f8cfb',
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
      }}
    />
  );
}
