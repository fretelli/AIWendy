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
  const { t, locale } = useI18n()
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
        description: locale === 'zh' ? '加载日志失败' : 'Failed to load journal entries',
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
        description: locale === 'zh' ? '删除日志失败' : 'Failed to delete journal entry',
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

  const getResultBadge = (result: TradeResult) => {
    const variants: Record<TradeResult, "default" | "secondary" | "destructive" | "outline"> = {
      [TradeResult.WIN]: "default",
      [TradeResult.LOSS]: "destructive",
      [TradeResult.BREAKEVEN]: "secondary",
      [TradeResult.OPEN]: "outline"
    }

    return (
      <Badge variant={variants[result]}>
        {result.toUpperCase()}
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
                <SelectItem value="breakeven">Breakeven</SelectItem>
                <SelectItem value="open">Open</SelectItem>
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
                  Page {currentPage} of {totalPages}
                </TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead>{locale === 'zh' ? '日期' : 'Date'}</TableHead>
                    <TableHead>{t('journal.symbol')}</TableHead>
                    <TableHead>{locale === 'zh' ? '方向' : 'Direction'}</TableHead>
                    <TableHead>{locale === 'zh' ? '结果' : 'Result'}</TableHead>
                    <TableHead className="text-right">{t('journal.pnl')}</TableHead>
                    <TableHead>{locale === 'zh' ? '规则' : 'Rules'}</TableHead>
                    <TableHead>{locale === 'zh' ? '信心' : 'Confidence'}</TableHead>
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
                          {journal.direction.toUpperCase()}
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
                          <Badge variant="outline" className="text-green-600">Followed</Badge>
                        ) : (
                          <Badge variant="destructive">Violated</Badge>
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
                  Previous
                </Button>
                <span className="flex items-center px-3 text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  Next
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{locale === 'zh' ? '确定删除？' : 'Are you sure?'}</AlertDialogTitle>
            <AlertDialogDescription>
              {locale === 'zh'
                ? '此操作无法撤销。这将永久删除您的日志记录。'
                : 'This action cannot be undone. This will permanently delete your journal entry.'}
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
