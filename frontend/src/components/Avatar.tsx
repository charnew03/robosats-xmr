import { avatarStyle, initialsFromPseudonym } from "../lib/avatar";

type Props = {
  pseudonym: string;
  size?: "sm" | "md" | "lg";
  className?: string;
};

const sizes = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
};

export function Avatar({ pseudonym, size = "md", className = "" }: Props) {
  const style = avatarStyle(pseudonym);
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center rounded-full font-semibold ${sizes[size]} ${className}`}
      style={style}
      title={pseudonym}
    >
      {initialsFromPseudonym(pseudonym)}
    </span>
  );
}
