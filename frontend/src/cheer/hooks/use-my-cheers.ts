import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { MatchesService, MeService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"

// 내가 응원 신청한 경기 → 응원팀 id (POST /matches/{id}/cheer 로 만든 기록)
export function useMyCheers() {
  return useQuery({
    queryKey: ["me", "records"],
    queryFn: async () => {
      const res = (await MeService.readMyRecords({ query: { size: 100 } })).data
      return new Map(res.data.map((r) => [r.match_id, r.cheered_team_id]))
    },
    enabled: isLoggedIn(),
    staleTime: 30_000,
  })
}

// 같은 경기에 다시 보내면 응원팀만 바뀐다 (종료된 경기는 409)
export function useCheerMatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ matchId, teamId }: { matchId: string; teamId: string }) =>
      MatchesService.cheerMatch({
        path: { id: matchId },
        body: { cheered_team_id: teamId },
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  })
}
