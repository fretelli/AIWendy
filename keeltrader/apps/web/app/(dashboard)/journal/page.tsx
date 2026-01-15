"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Plus, TrendingUp, TrendingDown, Minus, Eye, Edit, Trash2, Filter, BarChart3, Upload } from "lucide-react"
import { format } from "date-fns"

import { useI18n } from "@/lib/i18n/provider"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { journalApi } from "@/lib/api/journal"
import { JournalResponse, TradeResult, TradeDirection } from "@/lib/types/journal"
import { useToast } from "@/hooks/use-toast"
import { useActiveProjectId } from "@/lib/active-project"

export default function JournalPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const { projectId, ready } = useActiveProjectId()
  const [journals, setJournals] = useState<JournalResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [resultFilter, setResultFilter] = useState<string>("all")

  const fetchJournals = async () => {
    try {
      setLoading(true)
      const filter: any = {}
      if (projectId) {
        filter.project_id = projectId
      }
      if (resultFilter !== "all") {
        filter.result = resultFilter
      }

      const response = await journalApi.list({
        page: currentPage,
        per_page: 10,
        filter
      })

      setJournals(response.items)
      setTotalPages(Math.ceil(response.total / response.per_page))
    } catch (error) {
      toast({
        title: t('common.error'),
        description: t('journal.errors.load'),
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!ready) return
    fetchJournals()
  }, [currentPage, resultFilter, projectId, ready])

  const handleDelete = async () => {
    if (!deleteId) return

    try {
      await journalApi.delete(deleteId)
      toast({
        title: t('common.success'),
        description: t('success.deleted')
      })
      fetchJournals()
    } catch (error) {
      toast({
        title: t('common.error'),
        description: t('journal.errors.delete'),
        variant: "destructive"
      })
    } finally {
      setDeleteId(null)
    }
  }

  const getResultIcon = (result: TradeResult) => {
    switch (result) {
      case TradeResult.WIN:
        return <TrendingUp className="h-4 w-4 text-green-500" />
      case TradeResult.LOSS:
        return <TrendingDown className="h-4 w-4 text-red-500" />
      case TradeResult.BREAKEVEN:
        return <Minus className="h-4 w-4 text-gray-500" />
      default:
        return null
    }
  }

  const resultLabel = (result: TradeResult) => {
    if (result === TradeResult.WIN) return t('journal.results.win')
    if (result === TradeResult.LOSS) return t('journal.results.loss')
    if (result === TradeResult.BREAKEVEN) return t('journal.results.breakeven')
    if (result === TradeResult.OPEN) return t('journal.results.open')
    return result
  }

  const directionLabel = (direction: TradeDirection) => {
    if (direction === TradeDirection.LONG) return t('journal.long')
    if (direction === TradeDirection.SHORT) return t('journal.short')
    return direction
  }

  const getResultBadge = (result: TradeResult) => {
    const variants: Record<TradeResult, "default" | "secondary" | "destructive" | "outline"> = {
      [TradeResult.WIN]: "default",
      [TradeResult.LOSS]: "destructive",
      [TradeResult.BREAKEVEN]: "secondary",
      [TradeResult.OPEN]: "outline"
    }

    return (
      <Badge variant={variants[result]}>
        {resultLabel(result)}
      </Badge>
    )
  }

  const formatPnL = (amount?: number) => {
    if (!amount) return "-"
    const formatted = amount.toFixed(2)
    return amount >= 0 ? `+$${formatted}` : `-$${Math.abs(amount).toFixed(2)}`
  }

  return (
    <div className="container mx-auto max-w-7xl px-4 py-10 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">{t('journal.title')}</h1>
        <div className="flex gap-2">
          <Link href="/journal/stats">
            <Button variant="outline">
              <BarChart3 className="mr-2 h-4 w-4" />
              {t('journal.statistics')}
            </Button>
          </Link>
          <Link href="/journal/import">
            <Button variant="outline">
              <Upload className="mr-2 h-4 w-4" />
              {t('journal.import')}
            </Button>
          </Link>
          <Link href="/journal/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              {t('journal.addEntry')}
            </Button>
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>{t('journal.title')}</CardTitle>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            <Select value={resultFilter} onValueChange={setResultFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder={t('journal.filters')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                <SelectItem value="win">{t('journal.profitOnly')}</SelectItem>
                <SelectItem value="loss">{t('journal.lossOnly')}</SelectItem>
                <SelectItem value="breakeven">{resultLabel(TradeResult.BREAKEVEN)}</SelectItem>
                <SelectItem value="open">{resultLabel(TradeResult.OPEN)}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-10">{t('common.loading')}</div>
          ) : journals.length === 0 ? (
            <div className="text-center py-10">
              <p className="text-muted-foreground mb-4">{t('journal.noEntries')}</p>
              <div className="flex justify-center gap-2">
                <Link href="/journal/new">
                  <Button variant="outline">{t('journal.addFirstEntry')}</Button>
                </Link>
                <Link href="/journal/import">
                  <Button variant="outline">{t('journal.import')}</Button>
                </Link>
              </div>
            </div>
          ) : (
            <>
              <Table>
                <TableCaption>
                  {t('journal.pagination', { current: currentPage, total: totalPages })}
                </TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('journal.columns.date')}</TableHead>
                    <TableHead>{t('journal.symbol')}</TableHead>
                    <TableHead>{t('journal.columns.direction')}</TableHead>
                    <TableHead>{t('journal.columns.result')}</TableHead>
                    <TableHead className="text-right">{t('journal.pnl')}</TableHead>
                    <TableHead>{t('journal.columns.rules')}</TableHead>
                    <TableHead>{t('journal.columns.confidence')}</TableHead>
                    <TableHead className="text-right">{t('common.actions')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {journals.map((journal) => (
                    <TableRow key={journal.id}>
                      <TableCell>
                        {journal.trade_date
                          ? format(new Date(journal.trade_date), "MMM dd, yyyy")
                          : format(new Date(journal.created_at), "MMM dd, yyyy")
                        }
                      </TableCell>
                      <TableCell className="font-medium">{journal.symbol}</TableCell>
                      <TableCell>
                        <Badge variant={journal.direction === TradeDirection.LONG ? "default" : "secondary"}>
                          {directionLabel(journal.direction)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          {getResultIcon(journal.result)}
                          {getResultBadge(journal.result)}
                        </div>
                      </TableCell>
                      <TableCell className={`text-right font-medium ${
                        journal.pnl_amount && journal.pnl_amount >= 0 ? "text-green-500" : "text-red-500"
                      }`}>
                        {formatPnL(journal.pnl_amount)}
                      </TableCell>
                      <TableCell>
                        {journal.followed_rules ? (
                          <Badge variant="outline" className="text-green-600">{t('journal.rulesStatus.followed')}</Badge>
                        ) : (
                          <Badge variant="destructive">{t('journal.rulesStatus.violated')}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {journal.confidence_level
                          ? <span className="text-sm">{journal.confidence_level}/5</span>
                          : "-"
                        }
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex gap-1 justify-end">
                          <Link href={`/journal/${journal.id}`}>
                            <Button variant="ghost" size="sm">
                              <Eye className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Link href={`/journal/${journal.id}/edit`}>
                            <Button variant="ghost" size="sm">
                              <Edit className="h-4 w-4" />
                            </Button>
                          </Link>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeleteId(journal.id)}
                          >
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              <div className="flex justify-center gap-2 mt-6">
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  {t('common.previous')}
                </Button>
                <span className="flex items-center px-3 text-sm text-muted-foreground">
                  {t('journal.pagination', { current: currentPage, total: totalPages })}
                </span>
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  {t('common.next')}
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('journal.confirmDelete.title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('journal.confirmDelete.description')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>{t('common.delete')}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
