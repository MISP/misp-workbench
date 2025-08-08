import { storeToRefs } from "pinia";
import { useUserSettingsStore } from "@/stores";

export function isFollowingEntity(entityType, entityId) {
  const userSettingsStore = useUserSettingsStore();
  const { userSettings } = storeToRefs(userSettingsStore);

  return (
    userSettings?.value?.notifications?.follow?.[entityType]?.includes(
      entityId,
    ) || false
  );
}

export function toggleFollowEntity(entityType, entityId, followed) {
  const userSettingsStore = useUserSettingsStore();
  const { userSettings } = storeToRefs(userSettingsStore);

  const followed_entities =
    userSettings.value.notifications?.follow?.[entityType] || [];

  if (followed) {
    userSettingsStore.update("notifications", {
      follow: {
        ...userSettings.value.notifications?.follow,
        [entityType]: followed_entities.concat(entityId),
      },
    });
  } else {
    userSettingsStore.update("notifications", {
      follow: {
        ...userSettings.value.notifications?.follow,
        [entityType]: followed_entities.filter((uuid) => uuid !== entityId),
      },
    });
  }
}
