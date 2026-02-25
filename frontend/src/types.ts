export type SummaryResponse = {
  table_counts: Record<string, number>;
  recent_users: Array<{
    id: number;
    email: string;
    name: string;
    phone: string;
    created_at: string;
  }>;
  recent_patients: Array<{
    id: number;
    display_name: string | null;
    owner_user_id: number;
    created_at: string;
  }>;
};

export type SignUpPayload = {
  email: string;
  password: string;
  name: string;
  gender: "MALE" | "FEMALE";
  birth_date: string;
  phone_number: string;
};
