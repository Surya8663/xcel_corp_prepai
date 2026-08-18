interface StatCardProps {
  icon: string;
  iconVariant: "blue" | "green" | "purple" | "amber";
  label: string;
  value: string;
  delta?: string;
}

export default function StatCard({ icon, iconVariant, label, value, delta }: StatCardProps) {
  return (
    <div className="stat-card" role="region" aria-label={label}>
      <div className={`stat-card-icon ${iconVariant}`} aria-hidden="true">
        {icon}
      </div>
      <p className="stat-card-label">{label}</p>
      <p className="stat-card-value">{value}</p>
      {delta && <p className="stat-card-delta">{delta}</p>}
    </div>
  );
}
