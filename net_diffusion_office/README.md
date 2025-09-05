# NET-EASY Diffusion Office Module

## View Changes for Odoo 17.0

### Conditional Button Visibility

In Odoo 17.0, the `states` attribute has been deprecated in favor of using the `invisible` attribute with domain expressions. This change was made to provide a more consistent approach to conditional visibility in views.

#### Old approach (before Odoo 17.0):
```xml
<button name="action_confirm" string="Confirm" type="object" class="btn-primary" states="draft"/>
<button name="action_done" string="Mark as Done" type="object" class="btn-primary" states="confirmed"/>
<button name="action_cancel" string="Cancel" type="object" states="draft,confirmed"/>
<button name="action_draft" string="Set to Draft" type="object" states="cancel"/>
```

#### New approach (Odoo 17.0+):
```xml
<button name="action_confirm" string="Confirm" type="object" class="btn-primary" invisible="[('state', '!=', 'draft')]"/>
<button name="action_done" string="Mark as Done" type="object" class="btn-primary" invisible="[('state', '!=', 'confirmed')]"/>
<button name="action_cancel" string="Cancel" type="object" invisible="[('state', 'not in', ['draft', 'confirmed'])]"/>
<button name="action_draft" string="Set to Draft" type="object" invisible="[('state', '!=', 'cancel')]"/>
```

### Domain Expression Logic

The `invisible` attribute uses domain expressions to determine when an element should be hidden:

1. `invisible="[('state', '!=', 'draft')]"` - Button is visible only when state is 'draft'
2. `invisible="[('state', '!=', 'confirmed')]"` - Button is visible only when state is 'confirmed'
3. `invisible="[('state', 'not in', ['draft', 'confirmed'])]"` - Button is visible only when state is either 'draft' or 'confirmed'
4. `invisible="[('state', '!=', 'cancel')]"` - Button is visible only when state is 'cancel'

### Other Deprecated Attributes

In addition to `states`, the `attrs` attribute is also deprecated in Odoo 17.0. Instead, use the specific attributes directly with domain expressions:

- `invisible` - Controls visibility
- `readonly` - Controls whether a field is editable
- `required` - Controls whether a field is required

For example, instead of:
```xml
<field name="partner_id" attrs="{'readonly': [('state', '!=', 'draft')], 'required': [('state', '=', 'confirmed')]}"/>
```

Use:
```xml
<field name="partner_id" readonly="[('state', '!=', 'draft')]" required="[('state', '=', 'confirmed')]"/>
```

This change makes view definitions more consistent and easier to understand.