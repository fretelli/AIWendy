import { redirect } from "next/navigation";

export default function Page() { redirect("/agent/market?tab=macro&view=dashboard&period=1Y"); }
