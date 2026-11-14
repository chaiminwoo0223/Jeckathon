// 관람 신청(입장 초대장) 목록.
// 캘린더에서 응원 신청한 경기(POST /matches/{id}/cheer) 중 아직 끝나지 않은 경기를
// GET /communities/mine 으로 읽어, 화면이 쓰는 AppliedMatch 로 바꿔 넘긴다.
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { AxiosError } from "axios"
import { toast } from "sonner"
import {
  type AppliedMatch,
  formatTime,
  type InvitationState,
  type Team,
} from "@/cheer/data/mock"
import { toUiTeam } from "@/cheer/data/schedule"
import {
  CommunitiesService,
  type CommunityMineItem,
  type TeamPublic,
} from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"

// 화면 컴포넌트(티켓 좌석 번호, React key 등)는 목 타입의 숫자 id 를 쓴다.
// uuid 로 안정적인 숫자를 만들어 넣고, API 호출에는 matchId·communityId(uuid)를 쓴다.
function displayId(uuid: string): number {
  let h = 0
  for (let i = 0; i < uuid.length; i++) h = (h * 31 + uuid.charCodeAt(i)) | 0
  return Math.abs(h)
}

function toTeam(t: TeamPublic): Team {
  return { ...toUiTeam(t), id: displayId(t.id), league: t.league }
}

function toApplied(
  item: CommunityMineItem,
  clockOffsetMs: number,
): AppliedMatch {
  const m = item.match
  const home = toTeam(m.home_team)
  const away = toTeam(m.away_team)
  return {
    id: displayId(m.id),
    matchId: m.id,
    match: {
      id: displayId(m.id),
      home,
      away,
      league: m.league,
      kickoffAt: m.kickoff_at,
      status: m.status ?? "SCHEDULED",
      homeScore: m.home_score ?? undefined,
      awayScore: m.away_score ?? undefined,
    },
    cheeredTeam: item.cheered_team_id === m.home_team_id ? home : away,
    venue: m.venue ?? "",
    communityId: item.community.id,
    memberCount: item.community.member_count,
    joined: item.community.joined,
    enterOpensAt: item.enter_opens_at,
    clockOffsetMs,
  }
}

/** 내 관람 신청 내역 (끝나지 않은 경기, 경기 시작 오름차순) */
export function useAppliedMatches() {
  return useQuery({
    // 응원 신청(useCheerMatch)이 ["me"] 를 무효화하면 이 목록도 다시 읽는다
    queryKey: ["me", "applied-matches"],
    queryFn: async () => {
      const { data } = await CommunitiesService.readMyCommunities()
      // 입장 시각 비교는 서버 시계 기준 (브라우저 시계가 틀려도 버튼이 서버 규칙과 맞게)
      const offset = new Date(data.server_now).getTime() - Date.now()
      return data.days
        .flatMap((d) => d.items)
        .map((item) => toApplied(item, offset))
    },
    enabled: isLoggedIn(),
    refetchInterval: 60_000, // 경기 종료 처리된 경기가 목록에서 빠지도록
    retry: 1,
  })
}

/** 입장 가능 여부는 서버가 정한 입장 시작 시각(enter_opens_at) 기준. 목록에는 끝난 경기가 없다. */
export function entryState(
  am: AppliedMatch,
  now: Date = new Date(),
): InvitationState {
  const serverNow = now.getTime() + am.clockOffsetMs
  const diffMs = new Date(am.match.kickoffAt).getTime() - serverNow
  return {
    canEnter: serverNow >= new Date(am.enterOpensAt).getTime(),
    started: diffMs <= 0,
    minutesUntil: Math.ceil(diffMs / 60_000),
  }
}

type JoinErrorDetail = { code?: string; enter_opens_at?: string }

function joinErrorMessage(err: unknown): string {
  const detail =
    err instanceof AxiosError
      ? (err.response?.data as { detail?: JoinErrorDetail } | undefined)?.detail
      : undefined
  switch (detail?.code) {
    case "NOT_OPEN_YET":
      return detail.enter_opens_at
        ? `${formatTime(detail.enter_opens_at)}부터 입장할 수 있어요`
        : "아직 입장 시간이 아니에요"
    case "NOT_CHEERED":
      return "응원 신청한 경기만 입장할 수 있어요"
    case "MATCH_FINISHED":
      return "이미 끝난 경기예요"
    default:
      return "입장하지 못했어요. 다시 시도해 주세요"
  }
}

/** 초대장 → 커뮤니티 입장 (POST /communities/{id}/join, 이미 멤버여도 성공) */
export function useJoinCommunity() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (am: AppliedMatch) =>
      CommunitiesService.joinCommunity({ path: { id: am.communityId } }),
    onError: (err) => toast.error(joinErrorMessage(err)),
    // 입장 여부·인원 수가 바뀌었거나, 거절됐다면 목록 상태가 낡은 것이니 다시 읽는다
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["me", "applied-matches"] }),
  })
}
