unoc-grafana | logger=migrator t=2025-09-21T13:15:23.605669369Z level=info msg="Migration successfully executed" id="recreate alert_definition table" duration=733.739µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.614851552Z level=info msg="Executing migration" id="add index in alert_definition on org_id and title columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.615543098Z level=info msg="Migration successfully executed" id="add index in alert_definition on org_id and title columns" duration=691.943µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.624626759Z level=info msg="Executing migration" id="add index in alert_definition on org_id and uid columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.625368942Z level=info msg="Migration successfully executed" id="add index in alert_definition on org_id and uid columns" duration=740.825µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.634248535Z level=info msg="Executing migration" id="alter alert_definition table data column to mediumtext in mysql"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.634338536Z level=info msg="Migration successfully executed" id="alter alert_definition table data column to mediumtext in mysql" duration=92.817µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.64363139Z level=info msg="Executing migration" id="drop index in alert_definition on org_id and title columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.64439852Z level=info msg="Migration successfully executed" id="drop index in alert_definition on org_id and title columns" duration=769.364µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.652854835Z level=info msg="Executing migration" id="drop index in alert_definition on org_id and uid columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.653509105Z level=info msg="Migration successfully executed" id="drop index in alert_definition on org_id and uid columns" duration=652.194µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.662817271Z level=info msg="Executing migration" id="add unique index in alert_definition on org_id and title columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.663703837Z level=info msg="Migration successfully executed" id="add unique index in alert_definition on org_id and title columns" duration=885.182µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.672961374Z level=info msg="Executing migration" id="add unique index in alert_definition on org_id and uid columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.67366976Z level=info msg="Migration successfully executed" id="add unique index in alert_definition on org_id and uid columns" duration=707.602µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.682467804Z level=info msg="Executing migration" id="Add column paused in alert_definition"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.684910183Z level=info msg="Migration successfully executed" id="Add column paused in alert_definition" duration=2.44169ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.694062446Z level=info msg="Executing migration" id="drop alert_definition table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.69469178Z level=info msg="Migration successfully executed" id="drop alert_definition table" duration=629.644µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.703681527Z level=info msg="Executing migration" id="delete alert_definition_version table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.703812397Z level=info msg="Migration successfully executed" id="delete alert_definition_version table" duration=133.62µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.712975809Z level=info msg="Executing migration" id="recreate alert_definition_version table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.713639447Z level=info msg="Migration successfully executed" id="recreate alert_definition_version table" duration=664.161µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.722095987Z level=info msg="Executing migration" id="add index in alert_definition_version table on alert_definition_id and version columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.722954441Z level=info msg="Migration successfully executed" id="add index in alert_definition_version table on alert_definition_id and version columns" duration=857.801µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.732618151Z level=info msg="Executing migration" id="add index in alert_definition_version table on alert_definition_uid and version columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.733438683Z level=info msg="Migration successfully executed" id="add index in alert_definition_version table on alert_definition_uid and version columns" duration=820.305µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.742026653Z level=info msg="Executing migration" id="alter alert_definition_version table data column to mediumtext in mysql"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.742116188Z level=info msg="Migration successfully executed" id="alter alert_definition_version table data column to mediumtext in mysql" duration=92.394µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.751603604Z level=info msg="Executing migration" id="drop alert_definition_version table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.752229711Z level=info msg="Migration successfully executed" id="drop alert_definition_version table" duration=625.251µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.76171016Z level=info msg="Executing migration" id="create alert_instance table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.762576666Z level=info msg="Migration successfully executed" id="create alert_instance table" duration=865.763µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.771249898Z level=info msg="Executing migration" id="add index in alert_instance table on def_org_id, def_uid and current_state columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.77193784Z level=info msg="Migration successfully executed" id="add index in alert_instance table on def_org_id, def_uid and current_state columns" duration=683.837µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.781135625Z level=info msg="Executing migration" id="add index in alert_instance table on def_org_id, current_state columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.782188704Z level=info msg="Migration successfully executed" id="add index in alert_instance table on def_org_id, current_state columns" duration=1.05363ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.79065911Z level=info msg="Executing migration" id="add column current_state_end to alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.793106948Z level=info msg="Migration successfully executed" id="add column current_state_end to alert_instance" duration=2.446345ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.802584185Z level=info msg="Executing migration" id="remove index def_org_id, def_uid, current_state on alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.803272303Z level=info msg="Migration successfully executed" id="remove index def_org_id, def_uid, current_state on alert_instance" duration=689.723µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.811832257Z level=info msg="Executing migration" id="remove index def_org_id, current_state on alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.81258666Z level=info msg="Migration successfully executed" id="remove index def_org_id, current_state on alert_instance" duration=755.181µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.8220328Z level=info msg="Executing migration" id="rename def_org_id to rule_org_id in alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.832204818Z level=info msg="Migration successfully executed" id="rename def_org_id to rule_org_id in alert_instance" duration=10.172385ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.841390851Z level=info msg="Executing migration" id="rename def_uid to rule_uid in alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.853120416Z level=info msg="Migration successfully executed" id="rename def_uid to rule_uid in alert_instance" duration=11.726183ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.862814867Z level=info msg="Executing migration" id="add index rule_org_id, rule_uid, current_state on alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.863474646Z level=info msg="Migration successfully executed" id="add index rule_org_id, rule_uid, current_state on alert_instance" duration=660.477µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.872971371Z level=info msg="Executing migration" id="add index rule_org_id, current_state on alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.873745051Z level=info msg="Migration successfully executed" id="add index rule_org_id, current_state on alert_instance" duration=774.619µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.882466902Z level=info msg="Executing migration" id="add current_reason column related to current_state"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.884678855Z level=info msg="Migration successfully executed" id="add current_reason column related to current_state" duration=2.211541ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.893921338Z level=info msg="Executing migration" id="add result_fingerprint column to alert_instance"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.895990189Z level=info msg="Migration successfully executed" id="add result_fingerprint column to alert_instance" duration=2.068358ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.904463291Z level=info msg="Executing migration" id="create alert_rule table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.905365646Z level=info msg="Migration successfully executed" id="create alert_rule table" duration=903.033µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.915244334Z level=info msg="Executing migration" id="add index in alert_rule on org_id and title columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.915956146Z level=info msg="Migration successfully executed" id="add index in alert_rule on org_id and title columns" duration=712.343µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.924861235Z level=info msg="Executing migration" id="add index in alert_rule on org_id and uid columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.925883262Z level=info msg="Migration successfully executed" id="add index in alert_rule on org_id and uid columns" duration=1.02302ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.93537427Z level=info msg="Executing migration" id="add index in alert_rule on org_id, namespace_uid, group_uid columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.936162467Z level=info msg="Migration successfully executed" id="add index in alert_rule on org_id, namespace_uid, group_uid columns" duration=783.766µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.945338388Z level=info msg="Executing migration" id="alter alert_rule table data column to mediumtext in mysql"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.945431528Z level=info msg="Migration successfully executed" id="alter alert_rule table data column to mediumtext in mysql" duration=96.578µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.95457169Z level=info msg="Executing migration" id="add column for to alert_rule"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.956935291Z level=info msg="Migration successfully executed" id="add column for to alert_rule" duration=2.364881ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.965834012Z level=info msg="Executing migration" id="add column annotations to alert_rule"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.968072543Z level=info msg="Migration successfully executed" id="add column annotations to alert_rule" duration=2.238554ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.977527446Z level=info msg="Executing migration" id="add column labels to alert_rule"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.980749639Z level=info msg="Migration successfully executed" id="add column labels to alert_rule" duration=3.221358ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.989815276Z level=info msg="Executing migration" id="remove unique index from alert_rule on org_id, title columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:23.990762018Z level=info msg="Migration successfully executed" id="remove unique index from alert_rule on org_id, title columns" duration=946.033µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.000063201Z level=info msg="Executing migration" id="add index in alert_rule on org_id, namespase_uid and title columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.000776679Z level=info msg="Migration successfully executed" id="add index in alert_rule on org_id, namespase_uid and title columns" duration=713.535µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.009536818Z level=info msg="Executing migration" id="add dashboard_uid column to alert_rule"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.012446809Z level=info msg="Migration successfully executed" id="add dashboard_uid column to alert_rule" duration=2.905611ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.022129369Z level=info msg="Executing migration" id="add panel_id column to alert_rule"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.026329882Z level=info msg="Migration successfully executed" id="add panel_id column to alert_rule" duration=4.168962ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.037296294Z level=info msg="Executing migration" id="add index in alert_rule on org_id, dashboard_uid and panel_id columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.038757953Z level=info msg="Migration successfully executed" id="add index in alert_rule on org_id, dashboard_uid and panel_id columns" duration=1.463426ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.04831399Z level=info msg="Executing migration" id="add rule_group_idx column to alert_rule"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.051062672Z level=info msg="Migration successfully executed" id="add rule_group_idx column to alert_rule" duration=2.747859ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.060406974Z level=info msg="Executing migration" id="add is_paused column to alert_rule table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.06302401Z level=info msg="Migration successfully executed" id="add is_paused column to alert_rule table" duration=2.617327ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.072392305Z level=info msg="Executing migration" id="fix is_paused column for alert_rule table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.072470357Z level=info msg="Migration successfully executed" id="fix is_paused column for alert_rule table" duration=81.16µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.081318972Z level=info msg="Executing migration" id="create alert_rule_version table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.082745254Z level=info msg="Migration successfully executed" id="create alert_rule_version table" duration=1.422393ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.093011047Z level=info msg="Executing migration" id="add index in alert_rule_version table on rule_org_id, rule_uid and version columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.093754884Z level=info msg="Migration successfully executed" id="add index in alert_rule_version table on rule_org_id, rule_uid and version columns" duration=743.056µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.102696634Z level=info msg="Executing migration" id="add index in alert_rule_version table on rule_org_id, rule_namespace_uid and rule_group columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.103677753Z level=info msg="Migration successfully executed" id="add index in alert_rule_version table on rule_org_id, rule_namespace_uid and rule_group columns" duration=982.149µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.113135583Z level=info msg="Executing migration" id="alter alert_rule_version table data column to mediumtext in mysql"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.113222034Z level=info msg="Migration successfully executed" id="alter alert_rule_version table data column to mediumtext in mysql" duration=88.816µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.122726735Z level=info msg="Executing migration" id="add column for to alert_rule_version"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.125070312Z level=info msg="Migration successfully executed" id="add column for to alert_rule_version" duration=2.341294ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.133650211Z level=info msg="Executing migration" id="add column annotations to alert_rule_version"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.136300256Z level=info msg="Migration successfully executed" id="add column annotations to alert_rule_version" duration=2.64711ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.14534084Z level=info msg="Executing migration" id="add column labels to alert_rule_version"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.148662567Z level=info msg="Migration successfully executed" id="add column labels to alert_rule_version" duration=3.320298ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.157361375Z level=info msg="Executing migration" id="add rule_group_idx column to alert_rule_version"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.160042142Z level=info msg="Migration successfully executed" id="add rule_group_idx column to alert_rule_version" duration=2.67928ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.169846692Z level=info msg="Executing migration" id="add is_paused column to alert_rule_versions table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.172076947Z level=info msg="Migration successfully executed" id="add is_paused column to alert_rule_versions table" duration=2.229636ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.180658399Z level=info msg="Executing migration" id="fix is_paused column for alert_rule_version table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.180742487Z level=info msg="Migration successfully executed" id="fix is_paused column for alert_rule_version table" duration=86.418µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.190367108Z level=info msg="Executing migration" id=create_alert_configuration_table
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.190897783Z level=info msg="Migration successfully executed" id=create_alert_configuration_table duration=530.624µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.199527847Z level=info msg="Executing migration" id="Add column default in alert_configuration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.20228881Z level=info msg="Migration successfully executed" id="Add column default in alert_configuration" duration=2.760143ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.211907132Z level=info msg="Executing migration" id="alert alert_configuration alertmanager_configuration column from TEXT to MEDIUMTEXT if mysql"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.211984246Z level=info msg="Migration successfully executed" id="alert alert_configuration alertmanager_configuration column from TEXT to MEDIUMTEXT if mysql" duration=81.867µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.221660655Z level=info msg="Executing migration" id="add column org_id in alert_configuration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.224106193Z level=info msg="Migration successfully executed" id="add column org_id in alert_configuration" duration=2.444959ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.232763171Z level=info msg="Executing migration" id="add index in alert_configuration table on org_id column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.233657999Z level=info msg="Migration successfully executed" id="add index in alert_configuration table on org_id column" duration=896.259µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.242466778Z level=info msg="Executing migration" id="add configuration_hash column to alert_configuration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.244791062Z level=info msg="Migration successfully executed" id="add configuration_hash column to alert_configuration" duration=2.323755ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.261138037Z level=info msg="Executing migration" id=create_ngalert_configuration_table
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.261717967Z level=info msg="Migration successfully executed" id=create_ngalert_configuration_table duration=579.841µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.270229476Z level=info msg="Executing migration" id="add index in ngalert_configuration on org_id column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.270864597Z level=info msg="Migration successfully executed" id="add index in ngalert_configuration on org_id column" duration=633.464µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.279991455Z level=info msg="Executing migration" id="add column send_alerts_to in ngalert_configuration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.282274134Z level=info msg="Migration successfully executed" id="add column send_alerts_to in ngalert_configuration" duration=2.282435ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.290912476Z level=info msg="Executing migration" id="create provenance_type table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.291505505Z level=info msg="Migration successfully executed" id="create provenance_type table" duration=594.098µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.301311763Z level=info msg="Executing migration" id="add index to uniquify (record_key, record_type, org_id) columns"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.302281192Z level=info msg="Migration successfully executed" id="add index to uniquify (record_key, record_type, org_id) columns" duration=964.112µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.312440632Z level=info msg="Executing migration" id="create alert_image table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.313123672Z level=info msg="Migration successfully executed" id="create alert_image table" duration=683.82µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.322537341Z level=info msg="Executing migration" id="add unique index on token to alert_image table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.323208727Z level=info msg="Migration successfully executed" id="add unique index on token to alert_image table" duration=671.486µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.332599813Z level=info msg="Executing migration" id="support longer URLs in alert_image table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.332698517Z level=info msg="Migration successfully executed" id="support longer URLs in alert_image table" duration=102.102µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.341767384Z level=info msg="Executing migration" id=create_alert_configuration_history_table
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.342405735Z level=info msg="Migration successfully executed" id=create_alert_configuration_history_table duration=639.279µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.351714856Z level=info msg="Executing migration" id="drop non-unique orgID index on alert_configuration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.352383937Z level=info msg="Migration successfully executed" id="drop non-unique orgID index on alert_configuration" duration=670.067µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.360886927Z level=info msg="Executing migration" id="drop unique orgID index on alert_configuration if exists"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.361259062Z level=warn msg="Skipping migration: Already executed, but not recorded in migration log" id="drop unique orgID index on alert_configuration if exists"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.370978919Z level=info msg="Executing migration" id="extract alertmanager configuration history to separate table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.371485876Z level=info msg="Migration successfully executed" id="extract alertmanager configuration history to separate table" duration=505.786µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.380342602Z level=info msg="Executing migration" id="add unique index on orgID to alert_configuration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.381019505Z level=info msg="Migration successfully executed" id="add unique index on orgID to alert_configuration" duration=677.168µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.390206593Z level=info msg="Executing migration" id="add last_applied column to alert_configuration_history"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.393448702Z level=info msg="Migration successfully executed" id="add last_applied column to alert_configuration_history" duration=3.241113ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.402137558Z level=info msg="Executing migration" id="create library_element table v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.403183443Z level=info msg="Migration successfully executed" id="create library_element table v1" duration=1.04555ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.412300414Z level=info msg="Executing migration" id="add index library_element org_id-folder_id-name-kind"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.412994867Z level=info msg="Migration successfully executed" id="add index library_element org_id-folder_id-name-kind" duration=694.653µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.421472684Z level=info msg="Executing migration" id="create library_element_connection table v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.422120184Z level=info msg="Migration successfully executed" id="create library_element_connection table v1" duration=646.799µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.431007852Z level=info msg="Executing migration" id="add index library_element_connection element_id-kind-connection_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.431691039Z level=info msg="Migration successfully executed" id="add index library_element_connection element_id-kind-connection_id" duration=686.008µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.441494043Z level=info msg="Executing migration" id="add unique index library_element org_id_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.442127233Z level=info msg="Migration successfully executed" id="add unique index library_element org_id_uid" duration=635.946µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.450484323Z level=info msg="Executing migration" id="increase max description length to 2048"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.45051256Z level=info msg="Migration successfully executed" id="increase max description length to 2048" duration=29.434µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.459216896Z level=info msg="Executing migration" id="alter library_element model to mediumtext"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.45927058Z level=info msg="Migration successfully executed" id="alter library_element model to mediumtext" duration=54.56µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.467668835Z level=info msg="Executing migration" id="add library_element folder uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.470174402Z level=info msg="Migration successfully executed" id="add library_element folder uid" duration=2.505638ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.47916039Z level=info msg="Executing migration" id="populate library_element folder_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.479535008Z level=info msg="Migration successfully executed" id="populate library_element folder_uid" duration=375.142µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.488037246Z level=info msg="Executing migration" id="add index library_element org_id-folder_uid-name-kind"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.488926855Z level=info msg="Migration successfully executed" id="add index library_element org_id-folder_uid-name-kind" duration=889.573µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.500239034Z level=info msg="Executing migration" id="clone move dashboard alerts to unified alerting"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.500522887Z level=info msg="Migration successfully executed" id="clone move dashboard alerts to unified alerting" duration=284.065µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.509066818Z level=info msg="Executing migration" id="create data_keys table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.509758767Z level=info msg="Migration successfully executed" id="create data_keys table" duration=692.846µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.518768884Z level=info msg="Executing migration" id="create secrets table"  
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.519465207Z level=info msg="Migration successfully executed" id="create secrets table" duration=696.189µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.527948562Z level=info msg="Executing migration" id="rename data_keys name column to id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.543160284Z level=info msg="Migration successfully executed" id="rename data_keys name column to id" duration=15.210169ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.552638799Z level=info msg="Executing migration" id="add name column into data_keys"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.555020283Z level=info msg="Migration successfully executed" id="add name column into data_keys" duration=2.382176ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.563179256Z level=info msg="Executing migration" id="copy data_keys id column values into name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.563334581Z level=info msg="Migration successfully executed" id="copy data_keys id column values into name" duration=155.017µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.572551578Z level=info msg="Executing migration" id="rename data_keys name column to label"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.584088819Z level=info msg="Migration successfully executed" id="rename data_keys name column to label" duration=11.534501ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.592730617Z level=info msg="Executing migration" id="rename data_keys id column back to name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.605244964Z level=info msg="Migration successfully executed" id="rename data_keys id column back to name" duration=12.513971ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.614490095Z level=info msg="Executing migration" id="create kv_store table v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.615065788Z level=info msg="Migration successfully executed" id="create kv_store table v1" duration=575.821µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.623930112Z level=info msg="Executing migration" id="add index kv_store.org_id-namespace-key"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.624904111Z level=info msg="Migration successfully executed" id="add index kv_store.org_id-namespace-key" duration=973.524µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.634308359Z level=info msg="Executing migration" id="update dashboard_uid and panel_id from existing annotations"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.634572269Z level=info msg="Migration successfully executed" id="update dashboard_uid and panel_id from existing annotations" duration=262.757µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.643663402Z level=info msg="Executing migration" id="create permission table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.644343241Z level=info msg="Migration successfully executed" id="create permission table" duration=679.209µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.65288613Z level=info msg="Executing migration" id="add unique index permission.role_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.653508377Z level=info msg="Migration successfully executed" id="add unique index permission.role_id" duration=623.711µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.662082495Z level=info msg="Executing migration" id="add unique index role_id_action_scope"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.662809763Z level=info msg="Migration successfully executed" id="add unique index role_id_action_scope" duration=728.912µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.671856975Z level=info msg="Executing migration" id="create role table"  
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.672454964Z level=info msg="Migration successfully executed" id="create role table" duration=595.688µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.68148014Z level=info msg="Executing migration" id="add column display_name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.684626674Z level=info msg="Migration successfully executed" id="add column display_name" duration=3.145112ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.693456497Z level=info msg="Executing migration" id="add column group_name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.696159396Z level=info msg="Migration successfully executed" id="add column group_name" duration=2.702333ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.705274906Z level=info msg="Executing migration" id="add index role.org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.706142861Z level=info msg="Migration successfully executed" id="add index role.org_id" duration=869.992µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.715041208Z level=info msg="Executing migration" id="add unique index role_org_id_name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.715770984Z level=info msg="Migration successfully executed" id="add unique index role_org_id_name" duration=732.807µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.724935928Z level=info msg="Executing migration" id="add index role_org_id_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.725700545Z level=info msg="Migration successfully executed" id="add index role_org_id_uid" duration=762.401µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.734427403Z level=info msg="Executing migration" id="create team role table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.735085849Z level=info msg="Migration successfully executed" id="create team role table" duration=658.597µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.744664018Z level=info msg="Executing migration" id="add index team_role.org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.745442209Z level=info msg="Migration successfully executed" id="add index team_role.org_id" duration=777.62µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.753929127Z level=info msg="Executing migration" id="add unique index team_role_org_id_team_id_role_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.754666858Z level=info msg="Migration successfully executed" id="add unique index team_role_org_id_team_id_role_id" duration=737.971µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.763868163Z level=info msg="Executing migration" id="add index team_role.team_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.764782497Z level=info msg="Migration successfully executed" id="add index team_role.team_id" duration=914.76µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.773241384Z level=info msg="Executing migration" id="create user role table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.773834253Z level=info msg="Migration successfully executed" id="create user role table" duration=593.614µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.783066356Z level=info msg="Executing migration" id="add index user_role.org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.78383195Z level=info msg="Migration successfully executed" id="add index user_role.org_id" duration=765.839µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.792292281Z level=info msg="Executing migration" id="add unique index user_role_org_id_user_id_role_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.792995302Z level=info msg="Migration successfully executed" id="add unique index user_role_org_id_user_id_role_id" duration=701.686µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.802285276Z level=info msg="Executing migration" id="add index user_role.user_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.803025994Z level=info msg="Migration successfully executed" id="add index user_role.user_id" duration=741.359µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.811538996Z level=info msg="Executing migration" id="create builtin role table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.812309972Z level=info msg="Migration successfully executed" id="create builtin role table" duration=770.291µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.821860068Z level=info msg="Executing migration" id="add index builtin_role.role_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.822828056Z level=info msg="Migration successfully executed" id="add index builtin_role.role_id" duration=968.91µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.832370576Z level=info msg="Executing migration" id="add index builtin_role.name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.833158549Z level=info msg="Migration successfully executed" id="add index builtin_role.name" duration=788.343µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.84245067Z level=info msg="Executing migration" id="Add column org_id to builtin_role table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.845433628Z level=info msg="Migration successfully executed" id="Add column org_id to builtin_role table" duration=2.98251ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.854082213Z level=info msg="Executing migration" id="add index builtin_role.org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.854826216Z level=info msg="Migration successfully executed" id="add index builtin_role.org_id" duration=744.505µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.863661824Z level=info msg="Executing migration" id="add unique index builtin_role_org_id_role_id_role"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.864373701Z level=info msg="Migration successfully executed" id="add unique index builtin_role_org_id_role_id_role" duration=714.666µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.873391505Z level=info msg="Executing migration" id="Remove unique index role_org_id_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.87431199Z level=info msg="Migration successfully executed" id="Remove unique index role_org_id_uid" duration=921.253µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.882923906Z level=info msg="Executing migration" id="add unique index role.uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.883641307Z level=info msg="Migration successfully executed" id="add unique index role.uid" duration=718.335µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.893243911Z level=info msg="Executing migration" id="create seed assignment table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.893865455Z level=info msg="Migration successfully executed" id="create seed assignment table" duration=621.411µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.903733058Z level=info msg="Executing migration" id="add unique index builtin_role_role_name"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.904604586Z level=info msg="Migration successfully executed" id="add unique index builtin_role_role_name" duration=871.571µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.913743902Z level=info msg="Executing migration" id="add column hidden to role table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.917805324Z level=info msg="Migration successfully executed" id="add column hidden to role table" duration=4.059204ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.927858063Z level=info msg="Executing migration" id="permission kind migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.930812677Z level=info msg="Migration successfully executed" id="permission kind migration" duration=2.953541ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.939231119Z level=info msg="Executing migration" id="permission attribute migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.942444435Z level=info msg="Migration successfully executed" id="permission attribute migration" duration=3.21518ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.95153864Z level=info msg="Executing migration" id="permission identifier migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.954724855Z level=info msg="Migration successfully executed" id="permission identifier migration" duration=3.186597ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.963995799Z level=info msg="Executing migration" id="add permission identifier index"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.965055619Z level=info msg="Migration successfully executed" id="add permission identifier index" duration=1.060121ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.973950041Z level=info msg="Executing migration" id="add permission action scope role_id index"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.974624331Z level=info msg="Migration successfully executed" id="add permission action scope role_id index" duration=675.129µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.983445554Z level=info msg="Executing migration" id="remove permission role_id action scope index"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.984198756Z level=info msg="Migration successfully executed" id="remove permission role_id action scope index" duration=750.057µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.992835143Z level=info msg="Executing migration" id="create query_history table v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:24.993454276Z level=info msg="Migration successfully executed" id="create query_history table v1" duration=618.833µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.002394445Z level=info msg="Executing migration" id="add index query_history.org_id-created_by-datasource_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.003094315Z level=info msg="Migration successfully executed" id="add index query_history.org_id-created_by-datasource_uid" duration=700.376µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.011821078Z level=info msg="Executing migration" id="alter table query_history alter column created_by type to bigint"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.011891979Z level=info msg="Migration successfully executed" id="alter table query_history alter column created_by type to bigint" duration=71.965µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.021004852Z level=info msg="Executing migration" id="rbac disabled migrator"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.021061189Z level=info msg="Migration successfully executed" id="rbac disabled migrator" duration=59.86µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.029598177Z level=info msg="Executing migration" id="teams permissions migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.030054759Z level=info msg="Migration successfully executed" id="teams permissions migration" duration=457.478µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.039745818Z level=info msg="Executing migration" id="dashboard permissions"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.040279102Z level=info msg="Migration successfully executed" id="dashboard permissions" duration=534.738µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.049397567Z level=info msg="Executing migration" id="dashboard permissions uid scopes"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.050047577Z level=info msg="Migration successfully executed" id="dashboard permissions uid scopes" duration=651.432µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.059577189Z level=info msg="Executing migration" id="drop managed folder create actions"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.05980462Z level=info msg="Migration successfully executed" id="drop managed folder create actions" duration=227.956µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.06823933Z level=info msg="Executing migration" id="alerting notification permissions"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.068683444Z level=info msg="Migration successfully executed" id="alerting notification permissions" duration=444.601µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.077952671Z level=info msg="Executing migration" id="create query_history_star table v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.078509971Z level=info msg="Migration successfully executed" id="create query_history_star table v1" duration=557.429µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.086841113Z level=info msg="Executing migration" id="add index query_history.user_id-query_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.087576986Z level=info msg="Migration successfully executed" id="add index query_history.user_id-query_uid" duration=736.792µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.096778087Z level=info msg="Executing migration" id="add column org_id in query_history_star"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.09993966Z level=info msg="Migration successfully executed" id="add column org_id in query_history_star" duration=3.161144ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.108862314Z level=info msg="Executing migration" id="alter table query_history_star_mig column user_id type to bigint"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.108931705Z level=info msg="Migration successfully executed" id="alter table query_history_star_mig column user_id type to bigint" duration=72.375µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.117350347Z level=info msg="Executing migration" id="create correlation table v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.118108906Z level=info msg="Migration successfully executed" id="create correlation table v1" duration=758.624µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.126593994Z level=info msg="Executing migration" id="add index correlations.uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.127300593Z level=info msg="Migration successfully executed" id="add index correlations.uid" duration=705.594µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.136109398Z level=info msg="Executing migration" id="add index correlations.source_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.136834822Z level=info msg="Migration successfully executed" id="add index correlations.source_uid" duration=727.096µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.14573944Z level=info msg="Executing migration" id="add correlation config column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.14874611Z level=info msg="Migration successfully executed" id="add correlation config column" duration=3.006202ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.156919921Z level=info msg="Executing migration" id="drop index IDX_correlation_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.157607777Z level=info msg="Migration successfully executed" id="drop index IDX_correlation_uid - v1" duration=687.666µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.166497038Z level=info msg="Executing migration" id="drop index IDX_correlation_source_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.167434691Z level=info msg="Migration successfully executed" id="drop index IDX_correlation_source_uid - v1" duration=937.461µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.176144173Z level=info msg="Executing migration" id="Rename table correlation to correlation_tmp_qwerty - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.187231446Z level=info msg="Migration successfully executed" id="Rename table correlation to correlation_tmp_qwerty - v1" duration=11.08459ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.196443678Z level=info msg="Executing migration" id="create correlation v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.197301092Z level=info msg="Migration successfully executed" id="create correlation v2" duration=857.007µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.205906885Z level=info msg="Executing migration" id="create index IDX_correlation_uid - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.206753658Z level=info msg="Migration successfully executed" id="create index IDX_correlation_uid - v2" duration=846.395µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.217197725Z level=info msg="Executing migration" id="create index IDX_correlation_source_uid - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.218130262Z level=info msg="Migration successfully executed" id="create index IDX_correlation_source_uid - v2" duration=934.289µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.229200298Z level=info msg="Executing migration" id="create index IDX_correlation_org_id - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.23023425Z level=info msg="Migration successfully executed" id="create index IDX_correlation_org_id - v2" duration=1.035283ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.240789247Z level=info msg="Executing migration" id="copy correlation v1 to v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.241104254Z level=info msg="Migration successfully executed" id="copy correlation v1 to v2" duration=315.914µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.251473489Z level=info msg="Executing migration" id="drop correlation_tmp_qwerty"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.252123716Z level=info msg="Migration successfully executed" id="drop correlation_tmp_qwerty" duration=649.354µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.261014942Z level=info msg="Executing migration" id="add provisioning column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.264033061Z level=info msg="Migration successfully executed" id="add provisioning column" duration=3.013953ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.274261032Z level=info msg="Executing migration" id="create entity_events table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.274890673Z level=info msg="Migration successfully executed" id="create entity_events table" duration=627.716µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.284301181Z level=info msg="Executing migration" id="create dashboard public config v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.285189433Z level=info msg="Migration successfully executed" id="create dashboard public config v1" duration=886.364µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.293605332Z level=info msg="Executing migration" id="drop index UQE_dashboard_public_config_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.293914397Z level=warn msg="Skipping migration: Already executed, but not recorded in migration log" id="drop index UQE_dashboard_public_config_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.303128112Z level=info msg="Executing migration" id="drop index IDX_dashboard_public_config_org_id_dashboard_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.303385054Z level=warn msg="Skipping migration: Already executed, but not recorded in migration log" id="drop index IDX_dashboard_public_config_org_id_dashboard_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.311468732Z level=info msg="Executing migration" id="Drop old dashboard public config table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.312107065Z level=info msg="Migration successfully executed" id="Drop old dashboard public config table" duration=637.312µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.321164472Z level=info msg="Executing migration" id="recreate dashboard public config v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.321792316Z level=info msg="Migration successfully executed" id="recreate dashboard public config v1" duration=606.256µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.329976624Z level=info msg="Executing migration" id="create index UQE_dashboard_public_config_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.330709768Z level=info msg="Migration successfully executed" id="create index UQE_dashboard_public_config_uid - v1" duration=733.254µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.340031981Z level=info msg="Executing migration" id="create index IDX_dashboard_public_config_org_id_dashboard_uid - v1"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.34078231Z level=info msg="Migration successfully executed" id="create index IDX_dashboard_public_config_org_id_dashboard_uid - v1" duration=750.532µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.348822699Z level=info msg="Executing migration" id="drop index UQE_dashboard_public_config_uid - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.349608529Z level=info msg="Migration successfully executed" id="drop index UQE_dashboard_public_config_uid - v2" duration=785.242µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.358121317Z level=info msg="Executing migration" id="drop index IDX_dashboard_public_config_org_id_dashboard_uid - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.358748857Z level=info msg="Migration successfully executed" id="drop index IDX_dashboard_public_config_org_id_dashboard_uid - v2" duration=628.13µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.36742514Z level=info msg="Executing migration" id="Drop public config table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.368037847Z level=info msg="Migration successfully executed" id="Drop public config table" duration=612.045µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.376728189Z level=info msg="Executing migration" id="Recreate dashboard public config v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.377505125Z level=info msg="Migration successfully executed" id="Recreate dashboard public config v2" duration=777.321µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.386115346Z level=info msg="Executing migration" id="create index UQE_dashboard_public_config_uid - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.386799325Z level=info msg="Migration successfully executed" id="create index UQE_dashboard_public_config_uid - v2" duration=687.716µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.395117047Z level=info msg="Executing migration" id="create index IDX_dashboard_public_config_org_id_dashboard_uid - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.395940579Z level=info msg="Migration successfully executed" id="create index IDX_dashboard_public_config_org_id_dashboard_uid - v2" duration=822.416µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.404667848Z level=info msg="Executing migration" id="create index UQE_dashboard_public_config_access_token - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.405896275Z level=info msg="Migration successfully executed" id="create index UQE_dashboard_public_config_access_token - v2" duration=1.231831ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.415004851Z level=info msg="Executing migration" id="Rename table dashboard_public_config to dashboard_public - v2"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.423784967Z level=info msg="Migration successfully executed" id="Rename table dashboard_public_config to dashboard_public - v2" duration=8.779049ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.432389251Z level=info msg="Executing migration" id="add annotations_enabled column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.4355986Z level=info msg="Migration successfully executed" id="add annotations_enabled column" duration=3.208779ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.444607764Z level=info msg="Executing migration" id="add time_selection_enabled column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.448164246Z level=info msg="Migration successfully executed" id="add time_selection_enabled column" duration=3.55549ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.457060303Z level=info msg="Executing migration" id="delete orphaned public dashboards"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.45726501Z level=info msg="Migration successfully executed" id="delete orphaned public dashboards" duration=203.11µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.465850066Z level=info msg="Executing migration" id="add share column"  
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.468935072Z level=info msg="Migration successfully executed" id="add share column" duration=3.085857ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.477641896Z level=info msg="Executing migration" id="backfill empty share column fields with default of public"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.47784499Z level=info msg="Migration successfully executed" id="backfill empty share column fields with default of public" duration=204.366µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.486679074Z level=info msg="Executing migration" id="create file table"  
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.487280801Z level=info msg="Migration successfully executed" id="create file table" duration=601.552µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.495937244Z level=info msg="Executing migration" id="file table idx: path natural pk"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.496678855Z level=info msg="Migration successfully executed" id="file table idx: path natural pk" duration=739.891µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.505196452Z level=info msg="Executing migration" id="file table idx: parent_folder_path_hash fast folder retrieval"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.505917704Z level=info msg="Migration successfully executed" id="file table idx: parent_folder_path_hash fast folder retrieval" duration=721.213µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.515179996Z level=info msg="Executing migration" id="create file_meta table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.51576976Z level=info msg="Migration successfully executed" id="create file_meta table" duration=589.604µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.524619534Z level=info msg="Executing migration" id="file table idx: path key"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.525321282Z level=info msg="Migration successfully executed" id="file table idx: path key" duration=702.575µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.53406201Z level=info msg="Executing migration" id="set path collation in file table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.534129828Z level=info msg="Migration successfully executed" id="set path collation in file table" duration=69.322µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.542771255Z level=info msg="Executing migration" id="migrate contents column to mediumblob for MySQL"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.542847476Z level=info msg="Migration successfully executed" id="migrate contents column to mediumblob for MySQL" duration=78.24µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.551697708Z level=info msg="Executing migration" id="managed permissions migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.552088343Z level=info msg="Migration successfully executed" id="managed permissions migration" duration=393.091µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.560799304Z level=info msg="Executing migration" id="managed folder permissions alert actions migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.561030953Z level=info msg="Migration successfully executed" id="managed folder permissions alert actions migration" duration=232.465µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.569905688Z level=info msg="Executing migration" id="RBAC action name migrator"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.570808934Z level=info msg="Migration successfully executed" id="RBAC action name migrator" duration=903.846µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.579502528Z level=info msg="Executing migration" id="Add UID column to playlist"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.582721886Z level=info msg="Migration successfully executed" id="Add UID column to playlist" duration=3.2197ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.591362186Z level=info msg="Executing migration" id="Update uid column values in playlist"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.591506639Z level=info msg="Migration successfully executed" id="Update uid column values in playlist" duration=145.056µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.599973923Z level=info msg="Executing migration" id="Add index for uid in playlist"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.600706795Z level=info msg="Migration successfully executed" id="Add index for uid in playlist" duration=733.189µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.609674932Z level=info msg="Executing migration" id="update group index for alert rules"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.609994651Z level=info msg="Migration successfully executed" id="update group index for alert rules" duration=321.795µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.618551809Z level=info msg="Executing migration" id="managed folder permissions alert actions repeated migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.618818955Z level=info msg="Migration successfully executed" id="managed folder permissions alert actions repeated migration" duration=267.379µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.627610038Z level=info msg="Executing migration" id="admin only folder/dashboard permission"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.628096738Z level=info msg="Migration successfully executed" id="admin only folder/dashboard permission" duration=486.596µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.636729525Z level=info msg="Executing migration" id="add action column to seed_assignment"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.640057295Z level=info msg="Migration successfully executed" id="add action column to seed_assignment" duration=3.327821ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.648838857Z level=info msg="Executing migration" id="add scope column to seed_assignment"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.65335369Z level=info msg="Migration successfully executed" id="add scope column to seed_assignment" duration=4.509771ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.662457224Z level=info msg="Executing migration" id="remove unique index builtin_role_role_name before nullable update"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.663216962Z level=info msg="Migration successfully executed" id="remove unique index builtin_role_role_name before nullable update" duration=760.497µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.6719577Z level=info msg="Executing migration" id="update seed_assignment role_name column to nullable"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.707323036Z level=info msg="Migration successfully executed" id="update seed_assignment role_name column to nullable" duration=35.363468ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.716848496Z level=info msg="Executing migration" id="add unique index builtin_role_name back"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.717844514Z level=info msg="Migration successfully executed" id="add unique index builtin_role_name back" duration=995.502µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.727020837Z level=info msg="Executing migration" id="add unique index builtin_role_action_scope"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.727832603Z level=info msg="Migration successfully executed" id="add unique index builtin_role_action_scope" duration=812.131µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.737151546Z level=info msg="Executing migration" id="add primary key to seed_assigment"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.750573663Z level=info msg="Migration successfully executed" id="add primary key to seed_assigment" duration=13.419823ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.760578117Z level=info msg="Executing migration" id="add origin column to seed_assignment"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.764306332Z level=info msg="Migration successfully executed" id="add origin column to seed_assignment" duration=3.728403ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.774241051Z level=info msg="Executing migration" id="add origin to plugin seed_assignment"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.774521394Z level=info msg="Migration successfully executed" id="add origin to plugin seed_assignment" duration=282.164µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.783570982Z level=info msg="Executing migration" id="prevent seeding OnCall access"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.783749473Z level=info msg="Migration successfully executed" id="prevent seeding OnCall access" duration=181.592µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.793657477Z level=info msg="Executing migration" id="managed folder permissions alert actions repeated fixed migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.793877839Z level=info msg="Migration successfully executed" id="managed folder permissions alert actions repeated fixed migration" duration=223.133µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.802658251Z level=info msg="Executing migration" id="managed folder permissions library panel actions migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.802871729Z level=info msg="Migration successfully executed" id="managed folder permissions library panel actions migration" duration=213.707µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.812268721Z level=info msg="Executing migration" id="migrate external alertmanagers to datsourcse"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.812482673Z level=info msg="Migration successfully executed" id="migrate external alertmanagers to datsourcse" duration=214.72µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.821427151Z level=info msg="Executing migration" id="create folder table"  
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.822121455Z level=info msg="Migration successfully executed" id="create folder table" duration=694.288µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.830775371Z level=info msg="Executing migration" id="Add index for parent_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.831550853Z level=info msg="Migration successfully executed" id="Add index for parent_uid" duration=778.594µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.840813659Z level=info msg="Executing migration" id="Add unique index for folder.uid and folder.org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.841676948Z level=info msg="Migration successfully executed" id="Add unique index for folder.uid and folder.org_id" duration=863.226µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.85234172Z level=info msg="Executing migration" id="Update folder title length"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.852392494Z level=info msg="Migration successfully executed" id="Update folder title length" duration=53.621µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.861753034Z level=info msg="Executing migration" id="Add unique index for folder.title and folder.parent_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.862681795Z level=info msg="Migration successfully executed" id="Add unique index for folder.title and folder.parent_uid" duration=929.99µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.870960325Z level=info msg="Executing migration" id="Remove unique index for folder.title and folder.parent_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.871842149Z level=info msg="Migration successfully executed" id="Remove unique index for folder.title and folder.parent_uid" duration=882.341µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.880734311Z level=info msg="Executing migration" id="Add unique index for title, parent_uid, and org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.881559591Z level=info msg="Migration successfully executed" id="Add unique index for title, parent_uid, and org_id" duration=825.389µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.890371398Z level=info msg="Executing migration" id="Sync dashboard and folder table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.890771688Z level=info msg="Migration successfully executed" id="Sync dashboard and folder table" duration=400.395µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.900033059Z level=info msg="Executing migration" id="Remove ghost folders from the folder table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.90031177Z level=info msg="Migration successfully executed" id="Remove ghost folders from the folder table" duration=278.852µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.908956892Z level=info msg="Executing migration" id="Remove unique index UQE_folder_uid_org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.909818021Z level=info msg="Migration successfully executed" id="Remove unique index UQE_folder_uid_org_id" duration=863.09µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.918594047Z level=info msg="Executing migration" id="Add unique index UQE_folder_org_id_uid"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.919571169Z level=info msg="Migration successfully executed" id="Add unique index UQE_folder_org_id_uid" duration=977.5µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.929512863Z level=info msg="Executing migration" id="Remove unique index UQE_folder_title_parent_uid_org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.930434027Z level=info msg="Migration successfully executed" id="Remove unique index UQE_folder_title_parent_uid_org_id" duration=922.089µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.940168433Z level=info msg="Executing migration" id="Add unique index UQE_folder_org_id_parent_uid_title"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.941099656Z level=info msg="Migration successfully executed" id="Add unique index UQE_folder_org_id_parent_uid_title" duration=931.113µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.949741389Z level=info msg="Executing migration" id="Remove index IDX_folder_parent_uid_org_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.950511219Z level=info msg="Migration successfully executed" id="Remove index IDX_folder_parent_uid_org_id" duration=770.053µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.958727248Z level=info msg="Executing migration" id="create anon_device table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.959277006Z level=info msg="Migration successfully executed" id="create anon_device table" duration=550.294µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.968853475Z level=info msg="Executing migration" id="add unique index anon_device.device_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.969870265Z level=info msg="Migration successfully executed" id="add unique index anon_device.device_id" duration=1.017861ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.979305753Z level=info msg="Executing migration" id="add index anon_device.updated_at"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.979987398Z level=info msg="Migration successfully executed" id="add index anon_device.updated_at" duration=682.207µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.989825861Z level=info msg="Executing migration" id="create signing_key table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.990609519Z level=info msg="Migration successfully executed" id="create signing_key table" duration=783.322µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:25.999749045Z level=info msg="Executing migration" id="add unique index signing_key.key_id"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.000721574Z level=info msg="Migration successfully executed" id="add unique index signing_key.key_id" duration=974.464µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.010139967Z level=info msg="Executing migration" id="set legacy alert migration status in kvstore"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.01117623Z level=info msg="Migration successfully executed" id="set legacy alert migration status in kvstore" duration=1.038141ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.019720099Z level=info msg="Executing migration" id="migrate record of created folders during legacy migration to kvstore"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.019982969Z level=info msg="Migration successfully executed" id="migrate record of created folders during legacy migration to kvstore" duration=264.917µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.028906401Z level=info msg="Executing migration" id="Add folder_uid for dashboard"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.032595054Z level=info msg="Migration successfully executed" id="Add folder_uid for dashboard" duration=3.689343ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.042085065Z level=info msg="Executing migration" id="Populate dashboard folder_uid column"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.042667282Z level=info msg="Migration successfully executed" id="Populate dashboard folder_uid column" duration=584.984µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.051730775Z level=info msg="Executing migration" id="Add unique index for dashboard_org_id_folder_uid_title"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.051773029Z level=info msg="Migration successfully executed" id="Add unique index for dashboard_org_id_folder_uid_title" duration=46.106µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.060301844Z level=info msg="Executing migration" id="Delete unique index for dashboard_org_id_folder_id_title"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.060927039Z level=info msg="Migration successfully executed" id="Delete unique index for dashboard_org_id_folder_id_title" duration=625.953µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.06945835Z level=info msg="Executing migration" id="Delete unique index for dashboard_org_id_folder_uid_title"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.069479236Z level=info msg="Migration successfully executed" id="Delete unique index for dashboard_org_id_folder_uid_title" duration=22.408µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.078413821Z level=info msg="Executing migration" id="Add unique index for dashboard_org_id_folder_uid_title_is_folder"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.079201342Z level=info msg="Migration successfully executed" id="Add unique index for dashboard_org_id_folder_uid_title_is_folder" duration=786.784µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.087743374Z level=info msg="Executing migration" id="Restore index for dashboard_org_id_folder_id_title"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.08844046Z level=info msg="Migration successfully executed" id="Restore index for dashboard_org_id_folder_id_title" duration=696.629µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.097683828Z level=info msg="Executing migration" id="create sso_setting table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.09847561Z level=info msg="Migration successfully executed" id="create sso_setting table" duration=791.439µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.106787213Z level=info msg="Executing migration" id="copy kvstore migration status to each org"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.107403565Z level=info msg="Migration successfully executed" id="copy kvstore migration status to each org" duration=616.208µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.116977086Z level=info msg="Executing migration" id="add back entry for orgid=0 migrated status"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.117226721Z level=info msg="Migration successfully executed" id="add back entry for orgid=0 migrated status" duration=251.533µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.126355953Z level=info msg="Executing migration" id="alter kv_store.value to longtext"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.126499775Z level=info msg="Migration successfully executed" id="alter kv_store.value to longtext" duration=144.46µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.13631802Z level=info msg="Executing migration" id="add notification_settings column to alert_rule table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.13957612Z level=info msg="Migration successfully executed" id="add notification_settings column to alert_rule table" duration=3.257171ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.147890056Z level=info msg="Executing migration" id="add notification_settings column to alert_rule_version table"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.150926236Z level=info msg="Migration successfully executed" id="add notification_settings column to alert_rule_version table" duration=3.036356ms
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.160044072Z level=info msg="Executing migration" id="removing scope from alert.instances:read action migration"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.160314195Z level=info msg="Migration successfully executed" id="removing scope from alert.instances:read action migration" duration=269.272µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.168718124Z level=info msg="Executing migration" id="delete orphaned service account permissions"
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.169007829Z level=info msg="Migration successfully executed" id="delete orphaned service account permissions" duration=290.15µs
unoc-grafana | logger=migrator t=2025-09-21T13:15:26.178214384Z level=info msg="migrations completed" performed=552 skipped=0 duration=5.735845229s
unoc-grafana | logger=sqlstore t=2025-09-21T13:15:26.183010673Z level=info msg="Created default admin" user=admin
unoc-grafana | logger=sqlstore t=2025-09-21T13:15:26.183226396Z level=info msg="Created default organization"
unoc-grafana | logger=secrets t=2025-09-21T13:15:26.19469975Z level=info msg="Envelope encryption state" enabled=true currentprovider=secretKey.v1
unoc-grafana | logger=plugin.store t=2025-09-21T13:15:26.206421928Z level=info msg="Loading plugins..."
unoc-grafana | logger=local.finder t=2025-09-21T13:15:26.312665905Z level=warn msg="Skipping finding plugins as directory does not exist" path=/usr/share/grafana/plugins-bundled
unoc-grafana | logger=plugin.store t=2025-09-21T13:15:26.31269651Z level=info msg="Plugins loaded" count=55 duration=106.275101ms
unoc-grafana | logger=query_data t=2025-09-21T13:15:26.321115547Z level=info msg="Query Service initialization"
unoc-grafana | logger=live.push_http t=2025-09-21T13:15:26.326829134Z level=info msg="Live Push Gateway initialization"
unoc-grafana | logger=ngalert.migration t=2025-09-21T13:15:26.335773899Z level=info msg=Starting
unoc-grafana | logger=ngalert.migration t=2025-09-21T13:15:26.336087217Z level=info msg="Applying transition" currentType=Legacy desiredType=UnifiedAlerting cleanOnDowngrade=false cleanOnUpgrade=false
unoc-grafana | logger=ngalert.migration orgID=1 t=2025-09-21T13:15:26.336388387Z level=info msg="Migrating alerts for organisation"
unoc-grafana | logger=ngalert.migration orgID=1 t=2025-09-21T13:15:26.336790214Z level=info msg="Alerts found to migrate" alerts=0
unoc-grafana | logger=ngalert.migration t=2025-09-21T13:15:26.337799046Z level=info msg="Completed alerting migration"
unoc-grafana | logger=ngalert.state.manager t=2025-09-21T13:15:26.372170473Z level=info msg="Running in alternative execution of Error/NoData mode"
unoc-grafana | logger=infra.usagestats.collector t=2025-09-21T13:15:26.373494412Z level=info msg="registering usage stat providers" usageStatsProvidersLen=2
unoc-grafana | logger=provisioning.datasources t=2025-09-21T13:15:26.376058128Z level=info msg="inserting datasource from configuration" name=Prometheus uid=PBFA97CFB590B2093
unoc-grafana | logger=provisioning.alerting t=2025-09-21T13:15:26.390427132Z level=info msg="starting to provision alerting"  
unoc-grafana | logger=provisioning.alerting t=2025-09-21T13:15:26.390454204Z level=info msg="finished to provision alerting"  
unoc-grafana | logger=grafanaStorageLogger t=2025-09-21T13:15:26.390635114Z level=info msg="Storage starting"
unoc-grafana | logger=ngalert.state.manager t=2025-09-21T13:15:26.391255942Z level=info msg="Warming state cache for startup"  
unoc-grafana | logger=ngalert.multiorg.alertmanager t=2025-09-21T13:15:26.391375893Z level=info msg="Starting MultiOrg Alertmanager"
unoc-grafana | logger=http.server t=2025-09-21T13:15:26.39692912Z level=info msg="HTTP Server Listen" address=[::]:3000 protocol=http subUrl= socket=
unoc-grafana | logger=provisioning.dashboard t=2025-09-21T13:15:26.47377919Z level=info msg="starting to provision dashboards"  
unoc-grafana | logger=provisioning.dashboard t=2025-09-21T13:15:26.473808007Z level=info msg="finished to provision dashboards"
unoc-grafana | logger=ngalert.state.manager t=2025-09-21T13:15:26.493296585Z level=info msg="State cache has been initialized" states=0 duration=102.038323ms
unoc-grafana | logger=ngalert.scheduler t=2025-09-21T13:15:26.493338713Z level=info msg="Starting scheduler" tickInterval=10s maxAttempts=1
unoc-grafana | logger=ticker t=2025-09-21T13:15:26.49338355Z level=info msg=starting first_tick=2025-09-21T13:15:30Z
unoc-grafana | logger=grafana-apiserver t=2025-09-21T13:15:26.517923896Z level=info msg="Adding GroupVersion playlist.grafana.app v0alpha1 to ResourceManager"
unoc-grafana | logger=grafana-apiserver t=2025-09-21T13:15:26.518349299Z level=info msg="Adding GroupVersion featuretoggle.grafana.app v0alpha1 to ResourceManager"
unoc-grafana | logger=plugins.update.checker t=2025-09-21T13:15:26.545746032Z level=info msg="Update check succeeded" duration=153.792736ms
unoc-grafana | logger=grafana.update.checker t=2025-09-21T13:15:26.550271001Z level=info msg="Update check succeeded" duration=158.449135ms
unoc-grafana | logger=authn.service t=2025-09-21T13:15:28.421355812Z level=warn msg="Failed to authenticate request" client=auth.client.session error="user token not found"
unoc-grafana | logger=context userId=0 orgId=0 uname= t=2025-09-21T13:15:28.421440548Z level=info msg="Request Completed" method=GET path=/ status=302 remote_addr=172.18.0.1 time_ms=0 duration=519.479µs size=29 referer= handler=/ status_source=server  
unoc-grafana | logger=authn.service t=2025-09-21T13:15:28.425444585Z level=warn msg="Failed to authenticate request" client=auth.client.session error="user token not found"
unoc-grafana | logger=authn.service t=2025-09-21T13:15:36.280579306Z level=warn msg="Failed to authenticate request" client=auth.client.session error="user token not found"
unoc-grafana | logger=context userId=1 orgId=1 uname=admin t=2025-09-21T13:15:40.870046353Z level=info msg="Request Completed" method=GET path=/api/live/ws status=-1 remote_addr=172.18.0.1 time_ms=1 duration=1.462679ms size=0 referer= handler=/api/live/ws status_source=server
unoc-grafana | logger=context userId=1 orgId=1 uname=admin t=2025-09-21T13:16:38.298430634Z level=info msg="Request Completed" method=GET path=/api/plugins/grafana-llm-app/settings status=404 remote_addr=172.18.0.1 time_ms=0 duration=608.205µs size=64 referer=http://localhost:3000/explore handler=/api/plugins/:pluginId/settings status_source=server
unoc-grafana | logger=context userId=1 orgId=1 uname=admin t=2025-09-21T13:16:38.300186566Z level=info msg="Request Completed" method=GET path=/api/plugins/grafana-llm-app/settings status=404 remote_addr=172.18.0.1 time_ms=0 duration=505.865µs size=64 referer=http://localhost:3000/explore handler=/api/plugins/:pluginId/settings status_source=server
unoc-grafana | logger=infra.usagestats t=2025-09-21T13:16:53.229907057Z level=info msg="Usage stats are ready to report"  
(.venv) PS C:\noc_project\UNOC\unoc>
