import { redirect } from "next/navigation";

export default function Page() { redirect("/agent/market?tab=futures&period=1Y"); }
