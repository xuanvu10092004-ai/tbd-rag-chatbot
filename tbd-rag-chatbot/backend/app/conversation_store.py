"""
Module quan ly lich su hoi thoai trong bo nho (in-memory).

Ly do chon in-memory thay vi client.chats.create():
- Ung dung kiem soat hoan toan lich su: co the cat, loc, va dinh dang truoc khi gui Gemini
- Strict RAG: co the ngan Gemini su dung lich su lam nguon thong tin thuc te
- Fallback an toan: khong goi Gemini neu context trong (khong the lam voi session API)
- Don gian hon, de debug, phu hop cho demo local
- Moi conversation_id la mot UUID4 duy nhat

Luu y: Du lieu bi xoa khi backend khoi dong lai.
Neu can persistent conversation, can nang cap len database (ngoai scope hien tai).
"""

import logging
import uuid
from threading import Lock

from app.config import settings

logger = logging.getLogger(__name__)

# Kieu du lieu cho mot tin nhan
# {"role": "user" | "assistant", "content": str}
ConversationHistory = list[dict]


class ConversationStore:
    """
    Luu tru lich su hoi thoai trong RAM theo conversation_id (UUID4).
    Thread-safe bang su dung Lock.
    """

    def __init__(self) -> None:
        # Dict chinh: {conversation_id: list[dict]}
        self._store: dict[str, ConversationHistory] = {}
        # Lock de dam bao an toan khi co nhieu request dong thoi
        self._lock = Lock()

    def create_conversation(self) -> str:
        """
        Tao mot conversation moi voi ID duy nhat (UUID4).
        Khoi tao danh sach lich su rong cho conversation do.

        Returns:
            conversation_id dang chuoi UUID4
        """
        conversation_id = str(uuid.uuid4())
        with self._lock:
            self._store[conversation_id] = []
        logger.info("Da tao conversation moi: %s", conversation_id)
        return conversation_id

    def exists(self, conversation_id: str) -> bool:
        """
        Kiem tra conversation_id co hop le (ton tai trong store) khong.

        Args:
            conversation_id: ID can kiem tra

        Returns:
            True neu ton tai, False neu khong
        """
        with self._lock:
            return conversation_id in self._store

    def add_message(self, conversation_id: str, role: str, content: str) -> None:
        """
        Them mot tin nhan vao cuoi lich su hoi thoai.
        Tu dong cat cac tin nhan cu nhat neu vuot MAX_HISTORY_MESSAGES.

        Args:
            conversation_id: ID cua conversation
            role: "user" hoac "assistant"
            content: Noi dung tin nhan
        """
        if role not in ("user", "assistant"):
            logger.warning("Role khong hop le: '%s', phai la 'user' hoac 'assistant'", role)
            return

        with self._lock:
            # Neu conversation_id chua ton tai, tu dong tao moi
            if conversation_id not in self._store:
                self._store[conversation_id] = []
                logger.info("Tu dong tao conversation moi tu add_message: %s", conversation_id)

            # Them tin nhan moi
            self._store[conversation_id].append({"role": role, "content": content})

            # Cat bot cac tin nhan cu nhat neu vuot gioi han
            # Giu lai MAX_HISTORY_MESSAGES tin nhan gan nhat
            max_msgs = settings.MAX_HISTORY_MESSAGES
            if len(self._store[conversation_id]) > max_msgs:
                removed = len(self._store[conversation_id]) - max_msgs
                self._store[conversation_id] = self._store[conversation_id][-max_msgs:]
                logger.debug("Da cat %d tin nhan cu tu conversation %s", removed, conversation_id[:8])

    def get_history(self, conversation_id: str) -> ConversationHistory:
        """
        Lay danh sach lich su hoi thoai cua mot conversation.
        Tra ve list rong neu conversation_id khong ton tai.

        Args:
            conversation_id: ID cua conversation

        Returns:
            Danh sach dict [{"role": str, "content": str}]
        """
        with self._lock:
            return list(self._store.get(conversation_id, []))

    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Xoa lich su cua mot conversation (nhung giu lai conversation_id).

        Args:
            conversation_id: ID can xoa lich su

        Returns:
            True neu xoa thanh cong, False neu conversation_id khong ton tai
        """
        with self._lock:
            if conversation_id in self._store:
                self._store[conversation_id] = []
                logger.info("Da xoa lich su conversation: %s", conversation_id)
                return True
            return False

    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Xoa hoan toan mot conversation khoi store.

        Args:
            conversation_id: ID can xoa

        Returns:
            True neu xoa thanh cong
        """
        with self._lock:
            if conversation_id in self._store:
                del self._store[conversation_id]
                return True
            return False

    def get_total_count(self) -> int:
        """
        Lay tong so conversation dang luu tru (dung cho thong ke).
        """
        with self._lock:
            return len(self._store)


# Singleton store - duoc chia se giua tat ca cac request
conversation_store = ConversationStore()
