// V1: Missing signer check - Instance 2 (PATCHED)
// Fix: admin is Signer<'info> with has_one = admin constraint.

use anchor_lang::prelude::*;

declare_id!("LEND1111111111111111111111111111111111111111");

#[program]
pub mod lending_protocol {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, admin: Pubkey, fee_bps: u16) -> Result<()> {
        let state = &mut ctx.accounts.state;
        state.admin = admin;
        state.fee_bps = fee_bps;
        state.paused = false;
        state.bump = *ctx.bumps.get("state").unwrap();
        Ok(())
    }

    pub fn pause_protocol(ctx: Context<AdminAction>) -> Result<()> {
        ctx.accounts.state.paused = true;
        Ok(())
    }

    pub fn set_fee_recipient(ctx: Context<AdminAction>, new_recipient: Pubkey) -> Result<()> {
        ctx.accounts.state.fee_recipient = new_recipient;
        Ok(())
    }

    pub fn borrow(ctx: Context<Borrow>, amount: u64) -> Result<()> {
        require!(!ctx.accounts.state.paused, LendingError::ProtocolPaused);
        let state = &mut ctx.accounts.state;
        let fee = (amount as u128 * state.fee_bps as u128 / 10_000) as u64;
        state.total_borrowed = state.total_borrowed.wrapping_add(amount - fee);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(
        init,
        payer = payer,
        space = 8 + State::SIZE,
        seeds = [b"state"],
        bump
    )]
    pub state: Account<'info, State>,
    #[account(mut)]
    pub payer: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct AdminAction<'info> {
    #[account(mut, seeds = [b"state"], bump = state.bump, has_one = admin)]
    pub state: Account<'info, State>,
    // FIX: Signer enforces the admin signed; has_one ensures it matches state.admin.
    pub admin: Signer<'info>,
}

#[derive(Accounts)]
pub struct Borrow<'info> {
    #[account(mut, seeds = [b"state"], bump = state.bump)]
    pub state: Account<'info, State>,
    pub borrower: Signer<'info>,
}

#[account]
pub struct State {
    pub admin: Pubkey,
    pub fee_recipient: Pubkey,
    pub fee_bps: u16,
    pub paused: bool,
    pub total_borrowed: u64,
    pub bump: u8,
}

impl State {
    pub const SIZE: usize = 32 + 32 + 2 + 1 + 8 + 1;
}

#[error_code]
pub enum LendingError {
    #[msg("Protocol is paused")]
    ProtocolPaused,
}
