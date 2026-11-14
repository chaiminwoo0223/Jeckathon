import { useQuery } from "@tanstack/react-query"
import { MeService } from "@/client"
import { isLoggedIn } from "@/hooks/useAuth"

// 로그인 사용자의 CHEER 프로필(닉네임 등). 템플릿 UserPublic에는 닉네임이 없다
export const useMe = () =>
  useQuery({
    queryKey: ["me"],
    queryFn: async () => (await MeService.readMe()).data,
    enabled: isLoggedIn(),
  })
