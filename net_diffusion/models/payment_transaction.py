# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

from odoo import api, fields, models, SUPERUSER_ID, _
from dateutil.relativedelta import relativedelta
from datetime import date, datetime
import re
from pymongo import MongoClient, ASCENDING
from odoo.exceptions import ValidationError, UserError

import datetime

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _set_pending(self, state_message=None, extra_allowed_states=(), **kwargs):
        """ Override of `payment` to send the quotations automatically.

        :param str state_message: The reason for which the transaction is set in 'pending' state.
        :return: updated transactions.
        :rtype: `payment.transaction` recordset.
        """
        """ Update the transactions' state to `pending`.

        :param str state_message: The reason for setting the transactions in the state `pending`.
        :param tuple[str] extra_allowed_states: The extra states that should be considered allowed
                                                target states for the source state 'pending'.
        :return: The updated transactions.
        :rtype: recordset of `payment.transaction`
        """
        allowed_states = ('draft',)
        target_state = 'pending'
        txs_to_process = self._update_state(
            allowed_states + extra_allowed_states, target_state, state_message
        )
        txs_to_process._log_received_message()
        # txs_to_process = super()._set_pending(state_message=state_message, **kwargs)

        for tx in txs_to_process:  # Consider only transactions that are indeed set pending.
            sales_orders = tx.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent'])

            if tx.provider_id.code == 'custom':
                for so in tx.sale_order_ids:
                    # so.reference = tx._compute_sale_order_reference(so)
                    so.with_context(send_email=True).with_user(SUPERUSER_ID).action_confirm()
                    so.with_user(SUPERUSER_ID)._send_order_confirmation_mail()
            else:
                sales_orders.filtered(
                    lambda so: so.state == 'draft'
                ).with_context(tracking_disable=True).action_quotation_sent()

            # Send the payment status email.
            # The transactions are manually cached while in a sudoed environment to prevent an
            # AccessError: In some circumstances, sending the mail would generate the report assets
            # during the rendering of the mail body, causing a cursor commit, a flush, and forcing
            # the re-computation of the pending computed fields of the `mail.compose.message`,
            # including part of the template. Since that template reads the order's transactions and
            # the re-computation of the field is not done with the same environment, reading fields
            # that were not already available in the cache could trigger an AccessError (e.g., if
            # the payment was initiated by a public user).
            sales_orders.mapped('transaction_ids')
            sales_orders.filtered(
                    lambda so: so.state == 'draft'
                )._send_payment_succeeded_for_order_mail()

        return txs_to_process
