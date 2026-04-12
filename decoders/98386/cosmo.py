# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild
# type: ignore

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 11):
    raise Exception("Incompatible Kaitai Struct Python API: 0.11 or later is required, but you have %s" % (kaitaistruct.__version__))

class Cosmo(KaitaiStruct):
    """:field dest_callsign: ax25_frame.ax25_header.dest_callsign_raw.callsign_ror.callsign
    :field src_callsign: ax25_frame.ax25_header.src_callsign_raw.callsign_ror.callsign
    :field src_ssid: ax25_frame.ax25_header.src_ssid_raw.ssid
    :field dest_ssid: ax25_frame.ax25_header.dest_ssid_raw.ssid
    :field ctl: ax25_frame.ax25_header.ctl
    :field pid: ax25_frame.payload.pid
    :field ccsds_version: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.ccsds_version
    :field packet_type: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.packet_type
    :field secondary_header_flag: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.secondary_header_flag
    :field is_stored_data: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.is_stored_data
    :field application_process_id: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.application_process_id
    :field grouping_flag: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.grouping_flag
    :field sequence_count: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.sequence_count
    :field packet_length: ax25_frame.payload.ax25_info.ccsds_space_packet.packet_primary_header.packet_length
    :field time_stamp_seconds: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.secondary_header.time_stamp_seconds
    :field sub_seconds: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.secondary_header.sub_seconds
    :field padding: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.secondary_header.padding
    :field sc_fsw_28_ver: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_ver
    :field sc_fsw_28_type: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_type
    :field sc_fsw_28_sec_hdr_flag: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_sec_hdr_flag
    :field sc_fsw_28_pkt_apid: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_pkt_apid
    :field sc_fsw_28_seq_flgs: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_seq_flgs
    :field sc_fsw_28_seq_ctr: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_seq_ctr
    :field sc_fsw_28_pkt_len: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_pkt_len
    :field sc_fsw_28_shcoarse: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_shcoarse
    :field sc_fsw_28_shfine: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.sc_fsw_28_shfine
    :field bcn_adcs_tai_sec: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_tai_sec
    :field bcn_time_since_boot: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_time_since_boot
    :field bcn_hr_cyc_ct_safe: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_hr_cyc_ct_safe
    :field bcn_sec_in_mode: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sec_in_mode
    :field bcn_adcs_bod_rt_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_bod_rt_1
    :field bcn_adcs_bod_rt_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_bod_rt_2
    :field bcn_adcs_bod_rt_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_bod_rt_3
    :field bcn_adcs_att_resid_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_att_resid_1
    :field bcn_adcs_att_resid_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_att_resid_2
    :field bcn_adcs_att_resid_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_att_resid_3
    :field bcn_adcs_gps_pos_ecef_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_gps_pos_ecef_1
    :field bcn_adcs_gps_pos_ecef_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_gps_pos_ecef_2
    :field bcn_adcs_gps_pos_ecef_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_gps_pos_ecef_3
    :field bcn_cmd_rx_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_cmd_rx_ct
    :field bcn_cmd_rej_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_cmd_rej_ct
    :field bcn_cmd_succ_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_cmd_succ_ct
    :field bcn_pld_pass_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pass_ct
    :field bcn_pld_pass_err: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pass_err
    :field bcn_pld_pkt_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pkt_ct
    :field bcn_pld_5_v_0_reg_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_5_v_0_reg_t
    :field bcn_pld_3_v_3_reg_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_3_v_3_reg_t
    :field bcn_pld_sb_1_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_sb_1_t
    :field bcn_pld_sb_2_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_sb_2_t
    :field bcn_pld_vrum_t_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_vrum_t_1
    :field bcn_pld_vrum_t_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_vrum_t_2
    :field bcn_pld_pkt_rx_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pkt_rx_ct
    :field bcn_pld_pkt_ack_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pkt_ack_ct
    :field bcn_pld_pkt_nack_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pkt_nack_ct
    :field bcn_pld_err_reg_0_0: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_err_reg_0_0
    :field bcn_pld_err_reg_0_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_err_reg_0_1
    :field bcn_pld_err_reg_1_0: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_err_reg_1_0
    :field bcn_pld_err_reg_1_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_err_reg_1_1
    :field bcn_seq_exec_buf_auto: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_exec_buf_auto
    :field bcn_seq_exec_buf_op_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_exec_buf_op_1
    :field bcn_seq_exec_buf_op_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_exec_buf_op_2
    :field bcn_seq_exec_buf_op_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_exec_buf_op_3
    :field reusable_spare_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_1
    :field bcn_store_part_wr_log: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_wr_log
    :field bcn_store_part_rd_log: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_rd_log
    :field bcn_store_part_wr_adcs: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_wr_adcs
    :field bcn_store_part_rd_adcs: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_rd_adcs
    :field bcn_store_part_wr_hk: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_wr_hk
    :field bcn_store_part_rd_hk: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_rd_hk
    :field bcn_store_part_wr_sci: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_wr_sci
    :field bcn_store_part_rd_sci: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_store_part_rd_sci
    :field bcn_fp_resp_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_resp_ct
    :field bcn_bat_1_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_bat_1_v
    :field bcn_bat_2_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_bat_2_v
    :field bcn_bat_1_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_bat_1_t
    :field bcn_bat_2_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_bat_2_t
    :field bcn_3p3_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_3p3_i
    :field bcn_cdh_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_cdh_t
    :field bcn_sa_1_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sa_1_v
    :field bcn_sa_1_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sa_1_i
    :field bcn_sa_2_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sa_2_v
    :field bcn_sa_2_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sa_2_i
    :field bcn_eps_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_eps_t
    :field bcn_eps_bus_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_eps_bus_v
    :field bcn_eps_bus_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_eps_bus_i
    :field bcn_xact_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_xact_v
    :field bcn_xact_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_xact_i
    :field bcn_uhf_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_uhf_v
    :field bcn_uhf_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_uhf_i
    :field bcn_sbd_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sbd_v
    :field bcn_sbd_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sbd_i
    :field bcn_vrum_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_vrum_v
    :field bcn_vrum_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_vrum_i
    :field bcn_gps_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_gps_v
    :field bcn_gps_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_gps_i
    :field bcn_boom_v: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_boom_v
    :field bcn_boom_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_boom_i
    :field bcn_ifb_t_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_ifb_t_1
    :field bcn_adcs_rw_1_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_rw_1_t
    :field bcn_adcs_rw_sp_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_rw_sp_1
    :field bcn_adcs_rw_sp_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_rw_sp_2
    :field bcn_adcs_rw_sp_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_rw_sp_3
    :field bcn_sun_pt_err: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sun_pt_err
    :field bcn_mag_vec_bod_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_mag_vec_bod_1
    :field bcn_mag_vec_bod_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_mag_vec_bod_2
    :field bcn_mag_vec_bod_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_mag_vec_bod_3
    :field bcn_sbd_pa_i: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sbd_pa_i
    :field bcn_sbd_pa_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sbd_pa_t
    :field bcn_cmd_fail_code: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_cmd_fail_code
    :field bcn_vrum_cmd_rej_rsn: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_vrum_cmd_rej_rsn
    :field bcn_clt_hr_left: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_clt_hr_left
    :field bcn_clt_ct: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_clt_ct
    :field bcn_sys_mode: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_sys_mode
    :field bcn_uhf_alive: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_uhf_alive
    :field reusable_spare_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_2
    :field bcn_pld_pwr_cyc_vrum: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pwr_cyc_vrum
    :field bcn_pld_pwr_off_vrum: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pwr_off_vrum
    :field bcn_pld_stat_st_vrum: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_stat_st_vrum
    :field bcn_pld_time_st_vrum: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_time_st_vrum
    :field bcn_pld_alive_st_vrum: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_alive_st_vrum
    :field reusable_spare_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_3
    :field bcn_pld_pwr_cyc_boom: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pwr_cyc_boom
    :field bcn_pld_pwr_off_boom: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_pwr_off_boom
    :field bcn_pld_stat_st_boom: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_stat_st_boom
    :field bcn_pld_time_st_boom: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_time_st_boom
    :field bcn_pld_alive_st_boom: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pld_alive_st_boom
    :field bcn_uhf_t: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_uhf_t
    :field bcn_seq_state_auto: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_state_auto
    :field bcn_seq_state_op_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_state_op_1
    :field bcn_seq_state_op_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_state_op_2
    :field bcn_seq_state_op_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_seq_state_op_3
    :field reusable_spare_4: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_4
    :field reusable_spare_5: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_5
    :field reusable_spare_6: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_6
    :field reusable_spare_7: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_7
    :field reusable_spare_8: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_8
    :field reusable_spare_9: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_9
    :field bcn_htr_pwr_state_bat_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_htr_pwr_state_bat_2
    :field bcn_htr_pwr_state_bat_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_htr_pwr_state_bat_1
    :field reusable_spare_10: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.reusable_spare_10
    :field bcn_pwr_state_boom: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_boom
    :field bcn_pwr_state_gps: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_gps
    :field bcn_pwr_state_unused: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_unused
    :field bcn_pwr_state_vrum: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_vrum
    :field bcn_pwr_state_sbd: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_sbd
    :field bcn_pwr_state_uhf: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_uhf
    :field bcn_pwr_state_adcs: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_pwr_state_adcs
    :field bcn_fp_task_state: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_task_state
    :field bcn_fp_state_wp_23: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_23
    :field bcn_fp_state_wp_22: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_22
    :field bcn_fp_state_wp_21: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_21
    :field bcn_fp_state_wp_20: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_20
    :field bcn_fp_state_wp_19: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_19
    :field bcn_fp_state_wp_18: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_18
    :field bcn_fp_state_wp_17: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_17
    :field bcn_fp_state_wp_16: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_16
    :field bcn_fp_state_wp_15: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_15
    :field bcn_fp_state_wp_14: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_14
    :field bcn_fp_state_wp_13: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_13
    :field bcn_fp_state_wp_12: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_12
    :field bcn_fp_state_wp_11: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_11
    :field bcn_fp_state_wp_10: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_10
    :field bcn_fp_state_wp_9: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_9
    :field bcn_fp_state_wp_8: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_8
    :field bcn_fp_state_wp_7: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_7
    :field bcn_fp_state_wp_6: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_6
    :field bcn_fp_state_wp_5: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_5
    :field bcn_fp_state_wp_4: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_4
    :field bcn_fp_state_wp_3: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_3
    :field bcn_fp_state_wp_2: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_2
    :field bcn_fp_state_wp_1: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_1
    :field bcn_fp_state_wp_0: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_fp_state_wp_0
    :field bcn_adcs_alive: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_alive
    :field bcn_adcs_att_vld: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_att_vld
    :field bcn_adcs_ref_vld: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_ref_vld
    :field bcn_adcs_time_vld: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_time_vld
    :field bcn_adcs_mode: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_mode
    :field bcn_adcs_rec_sun_pt: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_rec_sun_pt
    :field bcn_adcs_sun_pt_state: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_sun_pt_state
    :field bcn_adcs_cmd_acc: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_cmd_acc
    :field bcn_adcs_cmd_fail: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_cmd_fail
    :field bcn_adcs_cmd_stat: ax25_frame.payload.ax25_info.ccsds_space_packet.data_section.user_data_field.beacon_t.bcn_adcs_cmd_stat
    """
    def __init__(self, _io, _parent=None, _root=None):
        super(Cosmo, self).__init__(_io)
        self._parent = _parent
        self._root = _root or self
        self._read()

    def _read(self):
        self.ax25_frame = Cosmo.Ax25Frame(self._io, self, self._root)


    def _fetch_instances(self):
        pass
        self.ax25_frame._fetch_instances()

    class Ax25Frame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.Ax25Frame, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.ax25_header = Cosmo.Ax25Header(self._io, self, self._root)
            _on = self.ax25_header.ctl & 19
            if _on == 0:
                pass
                self.payload = Cosmo.IFrame(self._io, self, self._root)
            elif _on == 16:
                pass
                self.payload = Cosmo.IFrame(self._io, self, self._root)
            elif _on == 18:
                pass
                self.payload = Cosmo.IFrame(self._io, self, self._root)
            elif _on == 19:
                pass
                self.payload = Cosmo.UiFrame(self._io, self, self._root)
            elif _on == 2:
                pass
                self.payload = Cosmo.IFrame(self._io, self, self._root)
            elif _on == 3:
                pass
                self.payload = Cosmo.UiFrame(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            self.ax25_header._fetch_instances()
            _on = self.ax25_header.ctl & 19
            if _on == 0:
                pass
                self.payload._fetch_instances()
            elif _on == 16:
                pass
                self.payload._fetch_instances()
            elif _on == 18:
                pass
                self.payload._fetch_instances()
            elif _on == 19:
                pass
                self.payload._fetch_instances()
            elif _on == 2:
                pass
                self.payload._fetch_instances()
            elif _on == 3:
                pass
                self.payload._fetch_instances()


    class Ax25Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.Ax25Header, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.dest_callsign_raw = Cosmo.CallsignRaw(self._io, self, self._root)
            self.dest_ssid_raw = Cosmo.SsidMask(self._io, self, self._root)
            self.src_callsign_raw = Cosmo.CallsignRaw(self._io, self, self._root)
            self.src_ssid_raw = Cosmo.SsidMask(self._io, self, self._root)
            self.ctl = self._io.read_u1()


        def _fetch_instances(self):
            pass
            self.dest_callsign_raw._fetch_instances()
            self.dest_ssid_raw._fetch_instances()
            self.src_callsign_raw._fetch_instances()
            self.src_ssid_raw._fetch_instances()


    class Ax25InfoData(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.Ax25InfoData, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.ccsds_space_packet = Cosmo.CcsdsSpacePacketT(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            self.ccsds_space_packet._fetch_instances()


    class BeaconT(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.BeaconT, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.bcn_adcs_tai_sec = self._io.read_f8be()
            self.bcn_time_since_boot = self._io.read_u4be()
            self.bcn_hr_cyc_ct_safe = self._io.read_u4be()
            self.bcn_sec_in_mode = self._io.read_u4be()
            self.bcn_adcs_bod_rt_1 = self._io.read_s4be()
            self.bcn_adcs_bod_rt_2 = self._io.read_s4be()
            self.bcn_adcs_bod_rt_3 = self._io.read_s4be()
            self.bcn_adcs_att_resid_1 = self._io.read_s4be()
            self.bcn_adcs_att_resid_2 = self._io.read_s4be()
            self.bcn_adcs_att_resid_3 = self._io.read_s4be()
            self.bcn_adcs_gps_pos_ecef_1 = self._io.read_s4be()
            self.bcn_adcs_gps_pos_ecef_2 = self._io.read_s4be()
            self.bcn_adcs_gps_pos_ecef_3 = self._io.read_s4be()
            self.bcn_cmd_rx_ct = self._io.read_u2be()
            self.bcn_cmd_rej_ct = self._io.read_u2be()
            self.bcn_cmd_succ_ct = self._io.read_u2be()
            self.bcn_pld_pass_ct = self._io.read_u2be()
            self.bcn_pld_pass_err = self._io.read_u2be()
            self.bcn_pld_pkt_ct = self._io.read_u2be()
            self.bcn_pld_5_v_0_reg_t = self._io.read_u2be()
            self.bcn_pld_3_v_3_reg_t = self._io.read_u2be()
            self.bcn_pld_sb_1_t = self._io.read_u2be()
            self.bcn_pld_sb_2_t = self._io.read_u2be()
            self.bcn_pld_vrum_t_1 = self._io.read_u2be()
            self.bcn_pld_vrum_t_2 = self._io.read_u2be()
            self.bcn_pld_pkt_rx_ct = self._io.read_u2be()
            self.bcn_pld_pkt_ack_ct = self._io.read_u2be()
            self.bcn_pld_pkt_nack_ct = self._io.read_u2be()
            self.bcn_pld_err_reg_0_0 = self._io.read_u2be()
            self.bcn_pld_err_reg_0_1 = self._io.read_u2be()
            self.bcn_pld_err_reg_1_0 = self._io.read_u2be()
            self.bcn_pld_err_reg_1_1 = self._io.read_u2be()
            self.bcn_seq_exec_buf_auto = self._io.read_u2be()
            self.bcn_seq_exec_buf_op_1 = self._io.read_u2be()
            self.bcn_seq_exec_buf_op_2 = self._io.read_u2be()
            self.bcn_seq_exec_buf_op_3 = self._io.read_u2be()
            self.reusable_spare_1 = self._io.read_u2be()
            self.bcn_store_part_wr_log = self._io.read_u4be()
            self.bcn_store_part_rd_log = self._io.read_u4be()
            self.bcn_store_part_wr_adcs = self._io.read_u4be()
            self.bcn_store_part_rd_adcs = self._io.read_u4be()
            self.bcn_store_part_wr_hk = self._io.read_u4be()
            self.bcn_store_part_rd_hk = self._io.read_u4be()
            self.bcn_store_part_wr_sci = self._io.read_u4be()
            self.bcn_store_part_rd_sci = self._io.read_u4be()
            self.bcn_fp_resp_ct = self._io.read_u2be()
            self.bcn_bat_1_v = self._io.read_u2be()
            self.bcn_bat_2_v = self._io.read_u2be()
            self.bcn_bat_1_t = self._io.read_u2be()
            self.bcn_bat_2_t = self._io.read_u2be()
            self.bcn_3p3_i = self._io.read_u2be()
            self.bcn_cdh_t = self._io.read_u2be()
            self.bcn_sa_1_v = self._io.read_u2be()
            self.bcn_sa_1_i = self._io.read_u2be()
            self.bcn_sa_2_v = self._io.read_u2be()
            self.bcn_sa_2_i = self._io.read_u2be()
            self.bcn_eps_t = self._io.read_u2be()
            self.bcn_eps_bus_v = self._io.read_u2be()
            self.bcn_eps_bus_i = self._io.read_u2be()
            self.bcn_xact_v = self._io.read_u2be()
            self.bcn_xact_i = self._io.read_u2be()
            self.bcn_uhf_v = self._io.read_u2be()
            self.bcn_uhf_i = self._io.read_u2be()
            self.bcn_sbd_v = self._io.read_u2be()
            self.bcn_sbd_i = self._io.read_u2be()
            self.bcn_vrum_v = self._io.read_u2be()
            self.bcn_vrum_i = self._io.read_u2be()
            self.bcn_gps_v = self._io.read_u2be()
            self.bcn_gps_i = self._io.read_u2be()
            self.bcn_boom_v = self._io.read_u2be()
            self.bcn_boom_i = self._io.read_u2be()
            self.bcn_ifb_t_1 = self._io.read_u2be()
            self.bcn_adcs_rw_1_t = self._io.read_s2be()
            self.bcn_adcs_rw_sp_1 = self._io.read_s2be()
            self.bcn_adcs_rw_sp_2 = self._io.read_s2be()
            self.bcn_adcs_rw_sp_3 = self._io.read_s2be()
            self.bcn_sun_pt_err = self._io.read_u2be()
            self.bcn_mag_vec_bod_1 = self._io.read_s2be()
            self.bcn_mag_vec_bod_2 = self._io.read_s2be()
            self.bcn_mag_vec_bod_3 = self._io.read_s2be()
            self.bcn_sbd_pa_i = self._io.read_u2be()
            self.bcn_sbd_pa_t = self._io.read_u2be()
            self.bcn_cmd_fail_code = self._io.read_u1()
            self.bcn_vrum_cmd_rej_rsn = self._io.read_u1()
            self.bcn_clt_hr_left = self._io.read_u1()
            self.bcn_clt_ct = self._io.read_u1()
            self.bcn_sys_mode = self._io.read_u1()
            self.bcn_uhf_alive = self._io.read_u1()
            self.reusable_spare_2 = self._io.read_bits_int_be(2)
            self.bcn_pld_pwr_cyc_vrum = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_pwr_off_vrum = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_stat_st_vrum = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_time_st_vrum = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_alive_st_vrum = self._io.read_bits_int_be(2)
            self.reusable_spare_3 = self._io.read_bits_int_be(2)
            self.bcn_pld_pwr_cyc_boom = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_pwr_off_boom = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_stat_st_boom = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_time_st_boom = self._io.read_bits_int_be(1) != 0
            self.bcn_pld_alive_st_boom = self._io.read_bits_int_be(2)
            self.bcn_uhf_t = self._io.read_s1()
            self.bcn_seq_state_auto = self._io.read_u1()
            self.bcn_seq_state_op_1 = self._io.read_u1()
            self.bcn_seq_state_op_2 = self._io.read_u1()
            self.bcn_seq_state_op_3 = self._io.read_u1()
            self.reusable_spare_4 = self._io.read_bits_int_be(1) != 0
            self.reusable_spare_5 = self._io.read_bits_int_be(1) != 0
            self.reusable_spare_6 = self._io.read_bits_int_be(1) != 0
            self.reusable_spare_7 = self._io.read_bits_int_be(1) != 0
            self.reusable_spare_8 = self._io.read_bits_int_be(1) != 0
            self.reusable_spare_9 = self._io.read_bits_int_be(1) != 0
            self.bcn_htr_pwr_state_bat_2 = self._io.read_bits_int_be(1) != 0
            self.bcn_htr_pwr_state_bat_1 = self._io.read_bits_int_be(1) != 0
            self.reusable_spare_10 = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_boom = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_gps = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_unused = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_vrum = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_sbd = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_uhf = self._io.read_bits_int_be(1) != 0
            self.bcn_pwr_state_adcs = self._io.read_bits_int_be(1) != 0
            self.bcn_fp_task_state = self._io.read_u1()
            self.bcn_fp_state_wp_23 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_22 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_21 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_20 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_19 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_18 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_17 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_16 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_15 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_14 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_13 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_12 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_11 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_10 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_9 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_8 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_7 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_6 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_5 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_4 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_3 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_2 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_1 = self._io.read_bits_int_be(2)
            self.bcn_fp_state_wp_0 = self._io.read_bits_int_be(2)
            self.bcn_adcs_alive = self._io.read_u1()
            self.bcn_adcs_att_vld = self._io.read_bits_int_be(1) != 0
            self.bcn_adcs_ref_vld = self._io.read_bits_int_be(1) != 0
            self.bcn_adcs_time_vld = self._io.read_bits_int_be(1) != 0
            self.bcn_adcs_mode = self._io.read_bits_int_be(1) != 0
            self.bcn_adcs_rec_sun_pt = self._io.read_bits_int_be(1) != 0
            self.bcn_adcs_sun_pt_state = self._io.read_bits_int_be(3)
            self.bcn_adcs_cmd_acc = self._io.read_u1()
            self.bcn_adcs_cmd_fail = self._io.read_u1()
            self.bcn_adcs_cmd_stat = self._io.read_u1()
            self.padding = self._io.read_u2be()
            self.padding2 = self._io.read_u1()
            self.checksum = self._io.read_u4be()


        def _fetch_instances(self):
            pass


    class Callsign(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.Callsign, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.callsign = (self._io.read_bytes(6)).decode(u"ASCII")
            if not  ((self.callsign == u"LASP  ") or (self.callsign == u"COSMO ")) :
                raise kaitaistruct.ValidationNotAnyOfError(self.callsign, self._io, u"/types/callsign/seq/0")


        def _fetch_instances(self):
            pass


    class CallsignRaw(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.CallsignRaw, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self._raw__raw_callsign_ror = self._io.read_bytes(6)
            self._raw_callsign_ror = KaitaiStream.process_rotate_left(self._raw__raw_callsign_ror, 8 - (1), 1)
            _io__raw_callsign_ror = KaitaiStream(BytesIO(self._raw_callsign_ror))
            self.callsign_ror = Cosmo.Callsign(_io__raw_callsign_ror, self, self._root)


        def _fetch_instances(self):
            pass
            self.callsign_ror._fetch_instances()


    class CcsdsSpacePacketT(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.CcsdsSpacePacketT, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self._raw_packet_primary_header = self._io.read_bytes(6)
            _io__raw_packet_primary_header = KaitaiStream(BytesIO(self._raw_packet_primary_header))
            self.packet_primary_header = Cosmo.PacketPrimaryHeaderT(_io__raw_packet_primary_header, self, self._root)
            self.data_section = Cosmo.DataSectionT(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            self.packet_primary_header._fetch_instances()
            self.data_section._fetch_instances()


    class CosmoBeaconT(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.CosmoBeaconT, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.beacon_t = Cosmo.BeaconT(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            self.beacon_t._fetch_instances()


    class DataSectionT(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.DataSectionT, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            if self._parent.packet_primary_header.secondary_header_flag:
                pass
                self._raw_secondary_header = self._io.read_bytes(6)
                _io__raw_secondary_header = KaitaiStream(BytesIO(self._raw_secondary_header))
                self.secondary_header = Cosmo.SecondaryHeaderT(_io__raw_secondary_header, self, self._root)

            _on = self._parent.packet_primary_header.application_process_id
            if _on == 28:
                pass
                self.user_data_field = Cosmo.CosmoBeaconT(self._io, self, self._root)


        def _fetch_instances(self):
            pass
            if self._parent.packet_primary_header.secondary_header_flag:
                pass
                self.secondary_header._fetch_instances()

            _on = self._parent.packet_primary_header.application_process_id
            if _on == 28:
                pass
                self.user_data_field._fetch_instances()


    class IFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.IFrame, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.pid = self._io.read_u1()
            self._raw_ax25_info = self._io.read_bytes_full()
            _io__raw_ax25_info = KaitaiStream(BytesIO(self._raw_ax25_info))
            self.ax25_info = Cosmo.Ax25InfoData(_io__raw_ax25_info, self, self._root)


        def _fetch_instances(self):
            pass
            self.ax25_info._fetch_instances()


    class PacketPrimaryHeaderT(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.PacketPrimaryHeaderT, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.ccsds_version = self._io.read_bits_int_be(3)
            self.packet_type = self._io.read_bits_int_be(1) != 0
            self.secondary_header_flag = self._io.read_bits_int_be(1) != 0
            self.is_stored_data = self._io.read_bits_int_be(1) != 0
            self.application_process_id = self._io.read_bits_int_be(10)
            self.grouping_flag = self._io.read_bits_int_be(2)
            self.sequence_count = self._io.read_bits_int_be(14)
            self.packet_length = self._io.read_u2be()


        def _fetch_instances(self):
            pass


    class SecondaryHeaderT(KaitaiStruct):
        """the secondary header is a feature of the space packet which allows
        additional types of information that may be useful to the user
        application (e.g., a time code) to be included.
        see: 4.1.3.2 in ccsds 133.0-b-1
        """
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.SecondaryHeaderT, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.time_stamp_seconds = self._io.read_u4be()
            self.sub_seconds = self._io.read_u2be()


        def _fetch_instances(self):
            pass


    class SsidMask(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.SsidMask, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.ssid_mask = self._io.read_u1()


        def _fetch_instances(self):
            pass

        @property
        def ssid(self):
            if hasattr(self, '_m_ssid'):
                return self._m_ssid

            self._m_ssid = (self.ssid_mask & 15) >> 1
            return getattr(self, '_m_ssid', None)


    class UiFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            super(Cosmo.UiFrame, self).__init__(_io)
            self._parent = _parent
            self._root = _root
            self._read()

        def _read(self):
            self.pid = self._io.read_u1()
            self._raw_ax25_info = self._io.read_bytes_full()
            _io__raw_ax25_info = KaitaiStream(BytesIO(self._raw_ax25_info))
            self.ax25_info = Cosmo.Ax25InfoData(_io__raw_ax25_info, self, self._root)


        def _fetch_instances(self):
            pass
            self.ax25_info._fetch_instances()



