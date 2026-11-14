import { useQuery } from "@tanstack/react-query"
import { MeService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"

// 로그인한 사용자의 CHEER 프로필 (닉네임·레벨·통계). 닉네임이 비면 백엔드가 이메일 앞부분으로 채운다
export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: async () => (await MeService.readMe()).data,
    enabled: isLoggedIn(),
    staleTime: 60_000,
  })
}
